# This file is part of the R package "aifeducation".
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as published by
# the Free Software Foundation.
#
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>

import torch 
import numpy as np
import math
import safetensors

#DenseLayer_stack_with_mask-----------------------------------------------------  
#Layer for creating a stack of dense layers with masking ability
# Returns a list with the following tensors
# * Input tensor
# * Sequence length of the tensors shape (Batch)
# * mask_times Mask on the level of complete sequences shape (Batch, Times)
# * mask_features Mask on the level of single features shape (Bath, Times, Features)
# True indicates that the sequence or is padded. If True these values should not be part 
# of further computations. mask_features is adapted to the new output size
class stack_dense_layer(torch.nn.Module):
  def __init__(self,times,hidden_size,n_layers,pad_value,dropout,act_fct="ELU",bias=True,normalization_type="LayerNorm",parametrizations="None",device=None, dtype=None,residual_type="None"):
    super().__init__()
    
    self.hidden_size=hidden_size
    self.n_layers=n_layers
    self.dropout=dropout
    self.bias=bias
    self.parametrizations=parametrizations
    self.act_fct=act_fct
    self.normalization_type=normalization_type
    self.times=times
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=torch.tensor(pad_value)
    
    self.residual_type=residual_type
    self.residual_connection=layer_residual_connection(self.residual_type,self.pad_value)  
    
    self.layer_list=torch.nn.ModuleList()
    for i in range(self.n_layers):
      tmp_layer=dense_layer_with_mask(
          input_size=self.hidden_size,
          output_size=self.hidden_size,
          times=self.times,
          act_fct=self.act_fct,
          bias=self.bias,
          dropout=self.dropout,
          pad_value=self.pad_value,
          parametrizations=self.parametrizations,
          device=device, 
          dtype=dtype,
          residual_type=self.residual_type,
          normalization_type=self.normalization_type
          )
      self.layer_list.append(tmp_layer)

  def forward(self,x,seq_len,mask_times,mask_features):
    tmp_x=x
    tmp_seq_len=seq_len
    tmp_mask_times=mask_times
    tmp_mask_features=mask_features
  
    for r in range(self.n_layers):
      current_layer=self.layer_list[r]
      res=current_layer(x=tmp_x,seq_len=tmp_seq_len,mask_times=tmp_mask_times,mask_features=tmp_mask_features)
      tmp_x=res[0]
      tmp_seq_len=res[1]
      tmp_mask_times=res[2]
      tmp_mask_features=res[3]
    
    #Residual Connection
    y=self.residual_connection(x=x,y=tmp_x,seq_len=tmp_seq_len,mask_times=tmp_mask_times,mask_features=tmp_mask_features)

    return y[0],y[1],y[2],y[3]
    
  def calc_output_shape(self):
    return self.output_size

#Recurrent Layer stack with mask
class stack_recurrent_layers(torch.nn.Module): 
  def __init__(self,times,hidden_size,n_layers,rec_type,rec_bidirectional,pad_value,dropout,bias=True,return_sequence=False,parametrizations="None",device=None, dtype=None,residual_type="None",normalization_type="LayerNorm"):
    super().__init__()
    self.hidden_size=hidden_size
    self.n_layers=n_layers
    self.rec_type=rec_type
    self.rec_bidirectional=rec_bidirectional
    self.dropout=dropout
    self.bias=bias
    self.parametrizations=parametrizations
    self.return_sequence=return_sequence
    self.times=times
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=torch.tensor(pad_value)
    
    self.pack_and_masking=layer_pack_and_masking()

    if rec_type=="GRU":
       self.rec_layers=torch.nn.GRU(
            input_size=self.hidden_size,
            hidden_size=self.hidden_size,
            num_layers=self.n_layers,
            dropout=self.dropout, 
            bidirectional=self.rec_bidirectional,
            bias=self.bias,
            device=device, 
            dtype=dtype,
            batch_first=True)
    elif rec_type=="LSTM":
       self.rec_layers=torch.nn.LSTM(
            input_size=self.hidden_size,
            hidden_size=self.hidden_size,
            num_layers=self.n_layers,
            dropout=self.dropout, 
            bidirectional=self.rec_bidirectional,
            bias=self.bias,
            device=device, 
            dtype=dtype,
            batch_first=True)
    if self.rec_bidirectional==True:
      self.compression_layer=dense_layer_with_mask(
        input_size=2*self.hidden_size,
        output_size=hidden_size,
        times=self.times,
        act_fct="ELU",
        dropout=0.0,
        bias=True,
        pad_value=self.pad_value,
        parametrizations="None",
        device=device, 
        dtype=dtype,
        normalization_type="None",
        residual_type="None"
      )

    self.unpack=layer_unpack_and_masking(sequence_length=self.times,pad_value=self.pad_value)
    
    self.residual_type=residual_type
    self.residual_connection=layer_residual_connection(self.residual_type,self.pad_value)  
    
  def forward(self,x,seq_len,mask_times,mask_features):
    y=self.pack_and_masking(x,seq_len,mask_times,mask_features)
    y=self.rec_layers(y[0])
    y=self.unpack(y[0],seq_len,mask_times,mask_features)
    if self.return_sequence==True:
      if self.rec_bidirectional==True:
        new_mask_features=self.calc_new_mask(mask_features)
        y=self.compression_layer(y[0],seq_len,mask_times,new_mask_features)
      y=self.residual_connection(x,y[0],y[1],y[2],y[3])
      return y[0],y[1],y[2],y[3]
    else:
      return y[1][-1,:,:]
    
  def calc_new_mask(self,mask_features):
    tmp_mask=torch.index_select(mask_features,2,torch.arange(start=0, end=1).to(device=mask_features.device))
    mask_features_new=tmp_mask.repeat(1,1,2*self.hidden_size)
    return mask_features_new
  
#stack_tf_encoder_layer--------------------------------
class stack_tf_encoder_layer(torch.nn.Module):
  def __init__(self,dense_dim,n_layers,times, features,pad_value,dropout_rate_1,dropout_rate_2,act_fct="ELU",attention_type="MultiHead",positional_embedding="absolute",num_heads=1,bias=True,parametrizations="None",normalization_type="LayerNorm",device=None, dtype=None,residual_type="None"):
    super().__init__()
    self.features=features
    self.dense_dim=dense_dim
    self.n_layers=n_layers
    self.attention_type=attention_type
    self.num_heads=num_heads
    self.times=times
    self.dropout_rate_1=dropout_rate_1
    self.dropout_rate_2=dropout_rate_2
    
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=torch.tensor(pad_value)
    self.bias=bias
    self.parametrizations=parametrizations
    self.positional_embedding=positional_embedding
    self.act_fct=act_fct
    self.normalization_type=normalization_type
    self.residual_type=residual_type
    
    self.layer_list=torch.nn.ModuleList()
    
    if self.positional_embedding=="absolute":
       self.positional_embedding_layer=layer_abs_positional_embedding(sequence_length=self.times,embedding_dim=self.features)
    elif self.positional_embedding=="None":
      self.positional_embedding_layer=identity_layer(pad_value=self.pad_value,apply_masking=True)
    
    for r in range(self.n_layers):
      self.layer_list.append(
        layer_tf_encoder(
          dense_dim=self.dense_dim,
          times=self.times, 
          features=self.features, 
          pad_value=self.pad_value,
          dropout_rate_1=self.dropout_rate_1,
          dropout_rate_2=self.dropout_rate_2,
          attention_type=self.attention_type,
          num_heads=self.num_heads,
          act_fct=self.act_fct,
          bias=self.bias,
          parametrizations=self.parametrizations,
          normalization_type=self.normalization_type,
          device=device, 
          dtype=dtype,
          residual_type=self.residual_type
         ))
    
    self.residual_type=residual_type
    self.residual_connection=layer_residual_connection(self.residual_type,self.pad_value) 

  def forward(self,x,seq_len,mask_times,mask_features):
    y=self.positional_embedding_layer(x)
    y=torch.where(mask_features,input=x,other=y)

    for r in range(self.n_layers):
      current_layer=self.layer_list[r]
      if r==0:
        y=current_layer(y,seq_len,mask_times,mask_features)
      else:
        y=current_layer(y[0],seq_len,mask_times,mask_features)
    
    #Residual connection
    y=self.residual_connection(x,y[0],seq_len,mask_times,mask_features)
    return y[0],y[1],y[2],y[3]

#stack_n_gram_convolution--------------------------------
class stack_n_gram_convolution(torch.nn.Module):
  def __init__(self,ks_min,ks_max,times,features,n_layers,pad_value,bias=True,dropout=0.1,parametrizations="None",device=None,dtype=None,act_fct="ELU",residual_type="None",normalization_type="LayerNorm"):
    super().__init__()
    
    self.features=features
    self.times=times
    self.n_layers=n_layers
    self.bias=bias
    self.parametrizations=parametrizations
    self.act_fct=act_fct
    self.residual_type=residual_type
    self.ks_min=ks_min
    self.ks_max=ks_max
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=torch.tensor(pad_value)
    
    self.layer_list=torch.nn.ModuleList()
    
    for r in range(self.n_layers):
      self.layer_list.append(
        layer_mutiple_n_gram_convolution(
          ks_min=self.ks_min,
          ks_max=self.ks_max,
          times=self.times,
          features=self.features,
          pad_value=self.pad_value,
          bias=self.bias,
          parametrizations=self.parametrizations,
          act_fct_name=self.act_fct,
          residual_type=residual_type,
          normalization_type=normalization_type,
          dropout=dropout,
          device=device, 
          dtype=dtype,
         ))
    
    self.residual_type=residual_type
    self.residual_connection=layer_residual_connection(self.residual_type,self.pad_value) 

  def forward(self,x,seq_len,mask_times,mask_features):
    for r in range(self.n_layers):
      current_layer=self.layer_list[r]
      if r==0:
        y=current_layer(x,seq_len,mask_times,mask_features)
      else:
        y=current_layer(y[0],seq_len,mask_times,mask_features)
    
    #Residual connection
    y=self.residual_connection(x,y[0],seq_len,mask_times, mask_features)
    return y[0],y[1],y[2],y[3]
