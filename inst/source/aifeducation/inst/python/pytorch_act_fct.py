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

def get_act_fct(name):
  if name=="ELU":
    return torch.nn.ELU()
  elif name=="LeakyReLU":
    return torch.nn.LeakyReLU()
  elif name=="ReLU":
    return torch.nn.ReLU()
  elif name=="GELU":
    return torch.nn.GELU()
  elif name=="Sigmoid":
    return torch.nn.Sigmoid()
  elif name=="Tanh":
    return torch.nn.Tanh()
  elif name=="PReLU":
    return torch.nn.PReLU()
  elif name=="None":
    return  torch.nn.Identity()


