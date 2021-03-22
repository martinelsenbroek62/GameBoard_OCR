#================================================================================
#!! DISABLE WARNINGS
#================================================================================
import os, warnings
warnings.filterwarnings('ignore')
import tensorflow as tf
os.environ["TF_CPP_MIN_LOG_LEVEL"]="2"  
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
#================================================================================

from const import *

from keras.models import *
from keras import *
from keras.optimizers import *
from keras.layers import *
from keras.regularizers import *
from keras.models import load_model 


import os,sys
import tensorflow as tf
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from keras import backend as K
num_cores = 7
num_GPU = 0
num_CPU = 1
config = tf.ConfigProto(intra_op_parallelism_threads=num_cores,\
        inter_op_parallelism_threads=num_cores, allow_soft_placement=True,\
        device_count = {'CPU' : num_CPU, 'GPU' : num_GPU})
session = tf.Session(config=config)
K.set_session(session)


def model_load(fname): 
	return load_model(fname)


_d = {'2':0,'3':1,'4':2,'5':3,'6':4,'7':5,'8':6,'9':7,'T':8,'J':9,'Q':10,'K':11,'A':12,'*':13}
_d_inv = {}
for x in _d:
	_d_inv[_d[x]] = x


#pred_input = np.zeros(shape=(1,96), dtype=float)
pred_input_15_5 = np.zeros(shape=(1,15,5,N_CHANNELS), dtype=float)

_model = None

def load_cod_model():
	model = model_load("data_cod/digits.pgz")
	return model

def model_predict(sample):
	global _model

	if _model is None:
		_model = load_cod_model()

	pred_input = pred_input_15_5
	pred_input[0] = sample.reshape(15,5,N_CHANNELS)
	o = _model.predict(pred_input)
	idx = np.argmax(o[0])
	return idx,o[0][idx]
