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

# Masking Layer------------------------------------------------------------------
# Layer for generating masking tensors
# Returns a list with the following tensors
# * Input tensor
# * Sequence length of the tensors shape (Batch)
# * mask_times Mask on the level of complete sequences shape (Batch, Times)
# * mask_features Mask on the level of single features shape (Batch, Times, Features)
# True indicates that the sequence or is padded. If True these values should not be part 
# of further computations
class masking_layer(torch.nn.Module):
  def __init__(self,pad_value):
    super().__init__()
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=pad_value
  def forward(self,x):
    features=x.size()[-1]
    device=('cuda' if torch.cuda.is_available() else 'cpu')
    time_sums=torch.sum(x,dim=2)
    #Get mask on the level of sequences/times
    mask_times=(time_sums==features*self.pad_value)
    #Get corresponding sequence length
    seq_len=torch.sum(~mask_times,dim=1)
    #Get mask for the level of features
    n_elements=seq_len*features
    mask_features=torch.reshape(torch.repeat_interleave(mask_times,repeats=features,dim=1),(x.size(dim=0),x.size(dim=1),features))
    #Bring values to device
    seq_len=seq_len.to(device)
    mask_times=mask_times.to(device)
    mask_features=mask_features.to(device)
    return x, seq_len, mask_times, mask_features

#Dropout layer with mask
class layer_dropout_with_mask(torch.nn.Module):
  def __init__(self,p=0.2, pad_value=-100):
      super().__init__()
      self.p=p
      self.dropout_layer=torch.nn.Dropout(p=self.p)
      
      if isinstance(pad_value, torch.Tensor):
        self.pad_value=pad_value.detach()
      else:
        self.pad_value=torch.tensor(pad_value)
  def forward(self,x,seq_len,mask_times,mask_features):
    y=self.dropout_layer(x)
    y_padded=torch.where(condition=mask_features,input=self.pad_value,other=y)
    return y_padded,seq_len,mask_times,mask_features
      
      


#Residual Connection layer----------------------------------------------------
class layer_residual_connection(torch.nn.Module):
    def __init__(self, type="None",pad_value=-100):
      super().__init__()
      self.type=type
      
      if isinstance(pad_value, torch.Tensor):
        self.pad_value=pad_value.detach()
      else:
        self.pad_value=torch.tensor(pad_value)
      
      if self.type=="ResidualGate":
        self.gate_param=torch.nn.Parameter(torch.ones(1))
      
    def forward(self, x,y,seq_len,mask_times,mask_features):
      if self.type=="None":
        return y, seq_len,mask_times,mask_features
      elif self.type=="Addition":
        z=x+y
        z=torch.where(condition=mask_features,input=self.pad_value,other=z)
        return z, seq_len,mask_times,mask_features
      elif self.type=="ResidualGate":
        weight=torch.nn.functional.sigmoid(self.gate_param)
        z=(1-weight)*x+weight*y
        torch.where(condition=mask_features,input=self.pad_value,other=z)
        return z, seq_len,mask_times,mask_features

class identity_layer(torch.nn.Module):
  def __init__(self,pad_value=None,apply_masking=True):
    super().__init__()
    if not pad_value==None:
      if isinstance(pad_value, torch.Tensor):
        self.pad_value=pad_value.detach()
      else:
        self.pad_value=torch.tensor(pad_value)
    self.apply_masking=apply_masking
  def forward(self,x,seq_len,mask_times,mask_features):
    if self.apply_masking==True:
      x=torch.where(condition=mask_features,input=self.pad_value,other=x)
    return x,seq_len,mask_times,mask_features

#DenseLayer_with_mask-----------------------------------------------------------
#Dense layer that can handel masked sequences
# Returns a list with the following tensors
# * Input tensor
# * Sequence length of the tensors shape (Batch)
# * mask_times Mask on the level of complete sequences shape (Batch, Times)
# * mask_features Mask on the level of single features shape (Bath, Times, Features)
# True indicates that the sequence or is padded. If True these values should not be part 
# of further computations. mask_features is adapted to the new output size
class dense_layer_with_mask(torch.nn.Module):
  def __init__(self,input_size,output_size,times,pad_value,act_fct="ELU",normalization_type="LayerNorm",dropout=0.0,bias=True,parametrizations="None",device=None, dtype=None,residual_type="None"):
    super().__init__()
    
    self.input_size=input_size
    self.output_size=output_size
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=torch.tensor(pad_value)
    self.times=times
    self.dropout=dropout
    self.bias=bias
    self.parametrizations=parametrizations
    self.act_fct_name=act_fct
    self.normalization_layer=get_layer_normalization(
      name=normalization_type,
      times=self.times,
      features=self.output_size,
      pad_value= self.pad_value,
      eps=1e-5)
    self.dense=torch.nn.Linear(
            in_features=self.input_size,
            out_features=self.output_size,
            bias=self.bias,
            device=device, 
            dtype=dtype
            )
    if self.parametrizations=="OrthogonalWeights":
      torch.nn.utils.parametrizations.orthogonal(module=self.dense, name='weight',orthogonal_map="matrix_exp")
    elif self.parametrizations=="WeightNorm":
      torch.nn.utils.parametrizations.weight_norm(module=self.dense, name='weight', dim=0)
    elif self.parametrizations=="SpectralNorm":
      torch.nn.utils.spectral_norm(module=self.dense, name='weight', n_power_iterations=1, eps=1e-12, dim=None)
    
    self.act_fct=get_act_fct(self.act_fct_name)
    
    if self.dropout >0:
      self.dropout=layer_dropout_with_mask(p=self.dropout,pad_value=self.pad_value)
    else:
      self.dropout=identity_layer(pad_value=self.pad_value,apply_masking=True)
    
    self.residual_connection=layer_residual_connection(residual_type,self.pad_value)  
      
  def forward(self,x,seq_len,mask_times,mask_features):
    #Calculate new mask on the feature level
    mask_features_new=self.calc_new_mask(mask_features=mask_features)
      
    #Calculate values
    y=self.dense(x)
    y=self.normalization_layer(y,seq_len,mask_times,mask_features_new)
    y_activation=self.act_fct(y[0])
    y=self.dropout(x=y_activation,seq_len=y[1],mask_times=y[2],mask_features=y[3])
    y=self.residual_connection(x=x,y=y[0],seq_len=y[1],mask_times=y[2],mask_features=y[3])
    
    #insert pad values
    #y_padded=torch.where(condition=mask_features_new,input=self.pad_value,other=y_dropout)
    
    #Return values
    return y[0],y[1],y[2],mask_features_new
  
  def calc_new_mask(self,mask_features):
    if self.input_size>self.output_size:
      mask_features_new=torch.index_select(mask_features,2,torch.arange(start=0, end=self.output_size).to(device=mask_features.device))
    elif self.input_size<self.output_size:
      tmp_mask=torch.index_select(mask_features,2,torch.arange(start=0, end=1).to(device=mask_features.device))
      mask_features_new=tmp_mask.repeat(1,1,self.output_size)
    else:
      mask_features_new=mask_features
    return mask_features_new

# Pooling Layer================================================================
#Extreme Pooling
#This layer provides different types of pooling. If pooling_type='max' it conductes
#a max pooling, if 'min' it conductes a min pooling, and if 'min_max' it combines both.
#In the last case the first half of tensors is for the max features and the second half
#for the min features.
#Input args:
#pooling_type: string Pooling type
#
#Returns a tensor with shape (Batch,Features) for "Min" and "Max" representing the min/max values over time 
#for every feature. If pooling type ="MinMax" shape is (Batch, 2*Features).
#Padding values cannot occure in the features and are not considered.
class exreme_pooling_over_time(torch.nn.Module):
  def __init__(self,times,features,pad_value,pooling_type="Max"):
    super().__init__()
    self.features=features
    self.kernel_size_times=times
    self.kernel_size_features=1
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=torch.tensor(pad_value)
    self.pooling_type=pooling_type
    
    self.n_filter_max=math.ceil(self.features/2)
    self.n_filter_min=self.features-self.n_filter_max
    
    self.pool_layer=torch.nn.MaxPool2d(
      kernel_size=(self.kernel_size_times, self.kernel_size_features), 
      stride=None, 
      padding=0, 
      dilation=1, 
      return_indices=False, 
      ceil_mode=False)

  def forward(self,x,mask_features):
    if self.pooling_type=="Max" or self.pooling_type=="MinMax":
      result_max=torch.squeeze(self.pool_layer(x),dim=1)
    if self.pooling_type=="Min" or self.pooling_type=="MinMax":
      tmp=(-1)*x
      tmp=torch.where(condition=mask_features,input=self.pad_value,other=tmp)
      result_min=torch.squeeze((-1)*self.pool_layer(tmp),dim=1)
    
    if self.pooling_type=="Max":
      return result_max
    elif self.pooling_type=="Min":
      return result_min
    elif self.pooling_type=="MinMax":
      return torch.cat((result_max,result_min),dim=1)


# Pooling over features
#Expects tensor of shape (Batch, Features)
#Returns tensor of shape (Bath, output_size)
class layer_adaptive_extreme_pooling_1d(torch.nn.Module):
  def __init__(self,output_size,pooling_type="Max"):
    super().__init__()
    
    self.output_size=output_size
    self.pooling_type=pooling_type
    
    self.n_out_max=math.ceil(self.output_size/2)
    self.n_out_min=self.output_size-self.n_out_max
    
  def get_max_n_values(self,x,n):
    y=x.sort(dim=1,descending=True)[0]
    y=torch.index_select(input=y,dim=1,index=torch.arange(start=0,end=n,step=1).to(device=y.device))
    return y
  def forward(self,x):
    y=x
    if self.pooling_type=="Max":
      z=self.get_max_n_values(y,self.output_size)
      return z
    elif self.pooling_type=="Min":
      z=(-1)*self.get_max_n_values((-1)*y,self.output_size)
      return z
    else:
      tmp_max=self.get_max_n_values(y,self.n_out_max)
      tmp_min=(-1)*self.get_max_n_values((-1)*y,self.n_out_min)
      return torch.cat((tmp_max,tmp_min),dim=1)

#n-Gram-Convolution
#This layer performs a n-gram convolution. The n-gram is determinted by parameter
#kernel_size_times. 
#Input args:
#kernel_size_times: int Length of the filter for the dimension times. Can be interpreted as n-gram.
#times: int Maximum length of the sequence
#features: int Number of features
# Returns a list with the following tensors
# * output tensor of shpae (Batch, Times, n_filter)
# * Sequence length of the tensors shape (Batch)
# * mask_times Mask on the level of complete sequences shape (Batch, Times)
# * mask_features Mask on the level of single features shape (Bath, Times, Features)
# True indicates that the sequence or is padded. If True these values should not be part 
# of further computations. mask_features is adapted to the new output size
#
class layer_n_gram_convolution(torch.nn.Module):
  def __init__(self, kernel_size_times, times, pad_value, n_filter, features, device=None, dtype=None,bias=True,parametrizations="None",act_fct="ELU"):
    super().__init__()
    self.times=times
    self.features=features
    self.parametrizations=parametrizations
    self.n_filters=n_filter
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=torch.tensor(pad_value)
    self.act_fct_name=act_fct

    self.kernel_size_times=kernel_size_times
    self.kernel_size_features=features
    self.stride=1
    self.dilation=1
    self.device=device 
    self.dtype=dtype
    self.bias=bias
    
    self.padding=self.calc_padding()
    
    self.conv_layer=torch.nn.Conv2d(
      in_channels=1, 
      out_channels=self.n_filters, 
      kernel_size=(kernel_size_times,self.kernel_size_features),
      stride=self.stride, 
      padding=0, 
      dilation=self.dilation, 
      groups=1, 
      bias=self.bias, 
      padding_mode='zeros',
      device=self.device, 
      dtype=self.dtype)
    self.act_fct=get_act_fct(self.act_fct_name)
    
    if self.parametrizations=="OrthogonalWeights":
      torch.nn.utils.parametrizations.orthogonal(module=self.conv_layer, name='weight',orthogonal_map="matrix_exp")
    elif self.parametrizations=="WeightNorm":
      torch.nn.utils.parametrizations.weight_norm(module=self.conv_layer, name='weight', dim=0)
    elif self.parametrizations=="SpectralNorm":
      torch.nn.utils.spectral_norm(module=self.conv_layer, name='weight', n_power_iterations=1, eps=1e-12, dim=None)
  
  def forward(self, x,seq_len,mask_times,mask_features):
    y=x*(~mask_features)
    y=torch.unsqueeze(y,dim=1)
    y=torch.nn.functional.pad(input=y,pad=self.padding,value=0)
    y=self.conv_layer(y)
    y=torch.squeeze(y,dim=3)
    y=torch.permute(input=y,dims=(0,2,1))
    y=self.act_fct(y)
    
    #Insert padding
    new_mask_features=self.calc_new_mask(mask_features=mask_features)
    y_padded=torch.where(condition=new_mask_features,input=self.pad_value,other=y)
    return y_padded,seq_len,mask_times,new_mask_features
    
  def calc_padding(self):
    padding_times=self.kernel_size_times-self.stride
    return 0,0, 0,padding_times
  
  def calc_new_mask(self,mask_features):
    if self.features>self.n_filters:
      mask_features_new=torch.index_select(mask_features,2,torch.arange(start=0, end=self.n_filters).to(device=mask_features.device))
    elif self.features<self.n_filters:
      tmp_mask=torch.index_select(mask_features,2,torch.arange(start=0, end=1).to(device=mask_features.device))
      mask_features_new=tmp_mask.repeat(1,1,self.n_filters)
    else:
      mask_features_new=mask_features
    return mask_features_new
  

#Multiple_n_gram_convolution
#n-Gram-Convolution
#This layer performs a n-gram convolution. The n-gram is determinted by parameter
#ks_min and ks_max. 
#Input args:
#kernel_size_times: int Length of the filter for the dimension times. Can be interpreted as n-gram.
#times: int Maximum length of the sequence
#features: int Number of features
# Returns a list with the following tensors
# * output tensor of shpae (Batch, Times, Features)
# The different sizes of n-grams determined with ks_min and ks_max are distrbuted equall in the resulting tensor.
# Every n-gram gets features/(ks_max-ks_min+1) features.
# * Sequence length of the tensors shape (Batch)
# * mask_times Mask on the level of complete sequences shape (Batch, Times)
# * mask_features Mask on the level of single features shape (Bath, Times, Features)
# True indicates that the sequence or is padded. If True these values should not be part 
# of further computations. 
#
class layer_mutiple_n_gram_convolution(torch.nn.Module):
  def __init__(self,ks_min,ks_max,times,features,pad_value,bias=True,dropout=0.1,parametrizations="None",device=None,dtype=None,act_fct_name="ELU",residual_type="ResidualGate",normalization_type="LayerNorm"):
    super().__init__() 
    self.ks_min=ks_min
    self.ks_max=ks_max
    self.num_n_grams=self.ks_max-self.ks_min+1
    self.features=features
    self.times=times
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=torch.tensor(pad_value)

    self.filters_per_ks=math.ceil(self.features/self.num_n_grams)
    self.n_filters_min=self.features-(self.num_n_grams-1)*self.filters_per_ks
    
    self.device=device
    self.dtype=dtype
    
    self.bias=bias
    self.parametrizations=parametrizations

    self.layer_list=torch.nn.ModuleList()
    
    for i in range(self.ks_min,self.ks_max+1):
      if not i==self.ks_max:
        tmp_n_filters=self.filters_per_ks
      else:
        tmp_n_filters=self.n_filters_min
      self.layer_list.append(
        layer_n_gram_convolution(
          kernel_size_times=i, 
          times=self.times, 
          n_filter=tmp_n_filters, 
          features=self.features, 
          device=self.device, 
          dtype=self.dtype,
          bias=self.bias,
          pad_value=self.pad_value,
          parametrizations=self.parametrizations,
          act_fct="None"
        )
      )
    
    self.act_fct_name=act_fct_name
    self.act_fct=get_act_fct(self.act_fct_name)
    self.normalization_layer=get_layer_normalization(
      name=normalization_type,
      times=self.times,
      features=self.features,
      pad_value= self.pad_value,
      eps=1e-5)
    
    self.dropout=dropout
    if self.dropout >0:
      self.dropout=layer_dropout_with_mask(p=self.dropout,pad_value=self.pad_value)
    else:
      self.dropout=identity_layer(pad_value=self.pad_value,apply_masking=True)
    
    self.residual_connection=layer_residual_connection(residual_type,self.pad_value) 
      
  def forward(self, x,seq_len,mask_times,mask_features):
    #Extract Features
    #Padding is insert within the layers. No Post-Processing required.
    for i in range(len(self.layer_list)):
      current_layer=self.layer_list[i]
      tmp=current_layer(x,seq_len,mask_times,mask_features)[0]
      if i==0:
        y=tmp
      else:
        y=torch.cat((y,tmp),dim=2)
    
    y=self.normalization_layer(x=y,seq_len=seq_len,mask_times=mask_times,mask_features=mask_features)    
    y_activation=self.act_fct(y[0])
    y=self.dropout(x=y_activation,seq_len=y[1],mask_times=y[2],mask_features=y[3])
    y=self.residual_connection(x=x,y=y[0],seq_len=y[1],mask_times=y[2],mask_features=y[3])
    
    return y[0],y[1],y[2],y[3]

#Pack and unpack layers
class layer_pack_and_masking(torch.nn.Module):
  def __init__(self):
    super().__init__()
  
  def forward(self,x,seq_len,mask_times,mask_features):
    x=torch.nn.utils.rnn.pack_padded_sequence(
    input=x,
    lengths=seq_len.to("cpu",dtype=torch.int),
    enforce_sorted=False, 
    batch_first=True)
    return x, seq_len,mask_times,mask_features

class layer_unpack_and_masking(torch.nn.Module):
  def __init__(self,sequence_length,pad_value):
    super().__init__()
    self.sequence_length=sequence_length
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=torch.tensor(pad_value)
    
  def forward(self,x,seq_len,mask_times,mask_features):
    x=torch.nn.utils.rnn.pad_packed_sequence(
    sequence=x,
    total_length=self.sequence_length,
    padding_value=self.pad_value,
    batch_first=True)[0]
    return x,seq_len,mask_times,mask_features

#layer transformer_encoder_fourier 
class layer_fourier_transformation(torch.nn.Module):
  def __init__(self):
    super().__init__()
    self.fourier_batch=torch.vmap(func=torch.fft.fft2,in_dims=0,out_dims=0)
    
  def forward(self,x):
    result=self.fourier_batch(x,norm="backward").real
    return result

#----------------
class layer_abs_positional_embedding(torch.nn.Module):
  def __init__(self, sequence_length,embedding_dim):
    super().__init__()
    self.sequence_length=sequence_length
    self.embedding_dim=embedding_dim
    
    self.embedding=torch.nn.Embedding(
      num_embeddings=self.sequence_length+1,
      embedding_dim=self.embedding_dim,
      padding_idx=0
    )
    
  def forward(self, x):
    mask=self.get_mask(x)
    device=('cuda' if torch.cuda.is_available() else 'cpu')

    input_seq=torch.arange(start=1, end=(self.sequence_length+1), step=1)
    input_seq=input_seq.to(device)
    
    input_seq=input_seq.repeat(x.shape[0], 1)
    input_seq.masked_fill_(mask,value=0)
    embedded_positions_masked=self.embedding(input_seq)
   
    return x+embedded_positions_masked
  
  def get_mask(self,x):
    device=('cuda' if torch.cuda.is_available() else 'cpu')
    time_sum=torch.sum(x,dim=2)
    time_sum=(time_sum!=0)
    masks=~time_sum
    masks=masks.to(device)
    return masks

#layer tf_encoder
class layer_tf_encoder(torch.nn.Module):
  def __init__(self, dense_dim,times, features,pad_value, dropout_rate_1,dropout_rate_2,attention_type="MultiHead",num_heads=2,act_fct="ELU",bias=True,parametrizations="None",normalization_type="LayerNorm",device=None, dtype=None,residual_type="None"):
    super().__init__()
    
    self.dense_dim=dense_dim
    
    self.dropout_rate_1=dropout_rate_1
    self.dropout_rate_2=dropout_rate_2
    
    self.features=features
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=torch.tensor(pad_value)
    self.times=times
    self.bias=bias
    self.parametrizations=parametrizations
    self.act_fct_name=act_fct
    self.normalization_type=normalization_type
    self.attention_type=attention_type
    self.num_heads=num_heads
   
    #Attention
    if self.attention_type=="MultiHead":
      self.attention=torch.nn.MultiheadAttention(
      embed_dim=self.features,
      num_heads=self.num_heads,
      dropout=0,
      batch_first=True,
      device=device, 
      dtype=dtype)
    elif self.attention_type=="Fourier":
      self.attention=layer_fourier_transformation()
    
    #Dropout Layer
    self.dropout_1=torch.nn.Dropout(p=self.dropout_rate_1)
    self.dropout_2=torch.nn.Dropout(p=self.dropout_rate_2)
    
    #Normalization Layer
    self.normalization_1=get_layer_normalization(
      name=self.normalization_type,
      times=self.times,
      features=self.features,
      pad_value=self.pad_value,
      eps=1e-5)
    self.normalization_2=get_layer_normalization(
      name=self.normalization_type,
      times=self.times,
      features=self.features,
      pad_value=self.pad_value,
      eps=1e-5)

    #Dense Layer
    self.dense_1=dense_layer_with_mask(
      input_size=self.features,
      output_size=self.dense_dim,
      times=self.times,
      act_fct=self.act_fct_name,
      dropout=0,
      bias=self.bias,
      pad_value=self.pad_value,
      parametrizations=self.parametrizations,
      device=device, 
      dtype=dtype,
      residual_type="None",
      normalization_type="None")
    self.dense_2=dense_layer_with_mask(
      input_size=self.dense_dim,
      output_size=self.features,
      times=self.times,
      act_fct="None",
      dropout=0,
      bias=self.bias,
      pad_value=self.pad_value,
      parametrizations=self.parametrizations,
      device=device, 
      dtype=dtype,
      residual_type="None",
      normalization_type="None")
    
    #Residual Layer
    self.residual_connection_1=layer_residual_connection(residual_type,self.pad_value)
    self.residual_connection_2=layer_residual_connection(residual_type,self.pad_value)

  def forward(self,x,seq_len,mask_times,mask_features):
    #Sub-Layer 1
    if self.attention_type=="Fourier":
      y=self.attention(x*(~mask_features))
    elif self.attention_type=="MultiHead":
      y=self.attention(
        query=x,
        key=x,
        value=x,
        key_padding_mask=mask_times)[0]
    y=self.dropout_1(y)
    y=torch.where(mask_features,input=self.pad_value,other=y)
    y=self.residual_connection_1(x=x,y=y,seq_len=seq_len,mask_times=mask_times,mask_features=mask_features)
    y=self.normalization_1(y[0],y[1],y[2],y[3])

    #Sub Layer 2    
    proj_output=self.dense_1(y[0],y[1],y[2],y[3])
    #Actvation function is part of dense_1. This it does not need a layer
    proj_output=self.dense_2(proj_output[0],proj_output[1],proj_output[2],proj_output[3])
    proj_dropout=self.dropout_2(proj_output[0])
    proj_dropout=torch.where(mask_features,input=self.pad_value,other=proj_dropout)
    
    output=self.residual_connection_2(x=y[0],y=proj_dropout,seq_len=seq_len,mask_times=mask_times,mask_features=mask_features)
    output=self.normalization_2(output[0],output[1],output[2],output[3])
    
    return output[0],output[1],output[2],output[3]
  


#Merge Leyer
class merge_layer(torch.nn.Module):
  def __init__(self,times,features,n_extracted_features,n_input_streams,pad_value,pooling_type="Max",normalization_type="None",attention_type="MultiHead",num_heads=1,device=None,dtype=None):
    super().__init__()
    
    self.times=times
    self.features=features
    if isinstance(pad_value, torch.Tensor):
      self.pad_value=pad_value.detach()
    else:
      self.pad_value=torch.tensor(pad_value)
    
    self.n_extracted_features=n_extracted_features
    self.n_input_streams=n_input_streams
    self.pooling_type=pooling_type
    self.attention_type=attention_type
    self.num_heads=num_heads
    
    self.normalization_type=normalization_type
    self.norm_layer_list=torch.nn.ModuleList()
    for r in range(self.n_input_streams):
      self.norm_layer_list.append(
        get_layer_normalization(name= self.normalization_type,times=self.times, features=self.features,pad_value=self.pad_value,eps=1e-5)
        )
    
    if pooling_type=="MinMax":
      self.n_pooling_features=2*self.features
    else:
      self.n_pooling_features=self.features
    
    self.pooling_layer=exreme_pooling_over_time(
      times=self.times,
      features=self.features,
      pooling_type=self.pooling_type,
      pad_value=self.pad_value
      )
      
    if self.attention_type=="MultiHead":  
      self.attention_layer=torch.nn.MultiheadAttention(
        embed_dim=self.n_pooling_features, 
        num_heads=self.num_heads, 
        dropout=0.0, 
        bias=True, 
        add_bias_kv=False, 
        add_zero_attn=False, 
        kdim=None, 
        vdim=None, 
        batch_first=True, 
        device=device, 
        dtype=dtype)
    elif self.attention_type=="Fourier":
      self.attention_layer=layer_fourier_transformation()
      
    self.act_fct=torch.nn.Softmax(dim=1)
    
    self.dense_weights=torch.nn.Linear(
      in_features=self.n_pooling_features*self.n_input_streams, 
      out_features=self.n_input_streams, 
      bias=True, 
      device=device, 
      dtype=dtype)
      
    self.pooling_over_features=layer_adaptive_extreme_pooling_1d(
      output_size=self.n_extracted_features,
      pooling_type=self.pooling_type)
      
      

  def forward(self,tensor_list,seq_len,mask_times,mask_features):
    #Extract features by pooling and conotate to a new sequence

    for r in range(self.n_input_streams):
      tmp_tensor=tensor_list[r]
      tmp_norm_layer=self.norm_layer_list[r]
      extracted=tmp_norm_layer(x=tmp_tensor,seq_len=seq_len,mask_times=mask_times,mask_features=mask_features)
      extracted=self.pooling_layer(extracted[0],extracted[3])
      extracted=torch.unsqueeze(extracted,dim=1)
      if r==0:
        extracted_seq=extracted
      else:
        extracted_seq=torch.cat((extracted_seq,extracted),dim=1)
      
    # calculate weights for merging
    if self.attention_type=="MultiHead":
      attn=self.attention_layer(extracted_seq,extracted_seq,extracted_seq)[0]
    elif self.attention_type=="Fourier":
      attn=self.attention_layer(extracted_seq)
    attn=torch.flatten(input=attn, start_dim=1, end_dim=-1)
    weights=self.act_fct(self.dense_weights(attn))
    weights=torch.unsqueeze(weights,dim=1)

    #Calculate finale representation
    final=torch.matmul(input=weights, other=extracted_seq)
    final=torch.squeeze(final,dim=1)
    final=self.pooling_over_features(final)
    return final


#Layer Class Mean
#Calculates the class mean for the given tensor and classes
#Input
# * x Tensor Embeddings of shape (Batch, Features)
# * classes Tensor with class indices starting at 0.
# * total_classes int tensor with the total number of classes.
#returns a tensor of shape (total_classes,Features)
class layer_class_mean(torch.nn.Module):
  def __init__(self):
    super().__init__()

  def forward(self,x,classes,total_classes):
    index_matrix=torch.nn.functional.one_hot(torch.Tensor.to(classes,dtype=torch.int64),num_classes=total_classes)
    index_matrix=torch.transpose(index_matrix,dim0=0,dim1=1)
    index_matrix=torch.Tensor.to(index_matrix,dtype=x.dtype)
    cases_per_class=torch.sum(index_matrix,dim=1)
    class_mean=torch.matmul(torch.diag(1/cases_per_class),torch.matmul(index_matrix,x))
    return class_mean

# Layer layer_protonet_metric
# Calculates the distance of sample to prototypes
# Input
# * x sample of Shape (Batch, Features)
# * prototypes Tensor of shape (num_classes, Features)
#Output Tensor of Shape (Batch, num_classes)
class layer_protonet_metric(torch.nn.Module):
  def __init__(self,metric_type="Euclidean"):
    super().__init__()
    self.alpha=torch.nn.Parameter((torch.ones(1)-1e-8))
    self.metric_type=metric_type
  
  def forward(self,x,prototypes):
    if self.metric_type=="Euclidean":
      distance_matrix=torch.cdist(
        x1=x,
        x2=prototypes,
        p=2.0
      )
    return self.get_scaling_factor()*distance_matrix
  def get_scaling_factor(self):
    return torch.sqrt(torch.square(self.alpha+1e-8))

#Global Pooling layer----------------------------------------------------------
class layer_global_average_pooling_1d(torch.nn.Module):
  def __init__(self,mask_type="attention"):
    super().__init__()
    self.mask_type=mask_type

  def forward(self,x,mask=None):
    if not mask is None:
      if not self.mask_type=="attention":
        applied_mask=~mask
      else:
        applied_mask=mask
      mask_r=applied_mask.reshape(applied_mask.size()[0],applied_mask.size()[1],1)
      x=torch.mul(x,mask_r)
    x=torch.sum(x,dim=1)*(1/self.get_length(x))
    return x
  
  def get_length(self,x):
    length=torch.sum(x,dim=2)
    length=(length!=0)
    length=torch.sum(length,dim=1).repeat(x.size(2),1)
    length=torch.transpose(length,dim0=0,dim1=1)
    return length
