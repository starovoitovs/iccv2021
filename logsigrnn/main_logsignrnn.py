 #!/usr/bin/env python
# coding: utf-8


import os
import pickle

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, FunctionTransformer
from tqdm import tqdm

from logsigrnn.utils import *
from logsigrnn.sigutils import *
from logsigrnn.dyadic_sigutils import *
from logsigrnn.vae import *
from logsigrnn.logsigrnn import *


# constants

N_JOINTS = 17
N_AXES = 3
N_PERSONS = 2
N_TIMESTEPS = 305


PATH_DATA = r"_input/train_new_data.npy"
PATH_LABELS = r"_input/train_new_label.pkl"
PATH_LABELS_DF = r"_input/train_new_label.csv"
PATH_LEARNING_CURVE = r"_output/learning.csv"
PATH_MODEL = r"_output/logsigrnn.hdf5"


# hyperparameters

# number of classes [0-155]; pick number smaller than 155 to learn less actions
PERMITTED = np.arange(155)
TUPLE_SIZE = 2
SIGNATURE_DEGREE = 2
N_SEGMENTS = 32,
BATCH_SIZE = 256
FILTER_SIZE_1 = 5
N_PROJECTION_NEURONS = 8
EPSILON_STD = 0.1
N_EPOCHS = 50
N_HIDDEN_NEURONS = 64
DROP_RATE_2 = 0.8
LEARNING_RATE = 0.001
VALIDATION_SPLIT = 0.15
TEST_SPLIT = 0.15


if __name__ == '__main__': 


    # %% load data

    X, y = load_data(PERMITTED, PATH_DATA, PATH_LABELS_DF)
    train_index, test_index = train_test_split(np.arange(len(X)), test_size=TEST_SPLIT, random_state=42)


    # %% prepare features and labels X, y for logsigrnn model
    reshape = FunctionTransformer(lambda data: data.transpose((0, 2, 3, 1, 4)).reshape((data.shape[0], data.shape[2], data.shape[3], -1)).astype(np.float32))


    # %% build model

    input_shape = (X.shape[0], X.shape[2], X.shape[3], X.shape[1] * X.shape[4])

    clf = build_logsigrnn_model(input_shape=input_shape,
                                projection_mode=1,
                                lstm_mode=0,
                                n_segments=N_SEGMENTS,
                                drop_rate_2=DROP_RATE_2,
                                signature_degree=SIGNATURE_DEGREE,
                                filter_size_1=FILTER_SIZE_1,
                                n_projection_neurons=N_PROJECTION_NEURONS,
                                n_joints=N_JOINTS,
                                n_classes=len(PERMITTED),
                                learning_rate=LEARNING_RATE,
                                n_hidden_neurons=N_HIDDEN_NEURONS)


    early_stopping_monitor = EarlyStopping(monitor='loss', min_delta=0, patience=20, verbose=0, mode='auto')
    reduce_lr = ReduceLROnPlateau(monitor='loss', patience=50, verbose=1, factor=0.8, min_lr=0.000001)
    mcp_save = ModelCheckpoint(PATH_MODEL, save_best_only=True, monitor='val_accuracy', mode='auto', save_weights_only=True)

    callbacks = [early_stopping_monitor, reduce_lr, mcp_save]

    pipeline = Pipeline([
        ('reshape', reshape),
        ('clf', clf),
    ])

    # param_grid = dict(n_segments=[4, 8, 16, 32, 64],
    #                   n_hidden_neurons=[64, 128, 256],
    #                   drop_rate_2=[0.5, 0.6, 0.7, 0.8, 0.9],
    #                   filter_size_2=[20, 40, 60, 80],
    #                   batch_size=[64, 128, 256, 512])

    pipeline.fit(X[train_index], y[train_index], clf__callbacks=callbacks, clf__epochs=N_EPOCHS, clf__batch_size=BATCH_SIZE, clf__validation_split=VALIDATION_SPLIT)
    # cross_validate(model, n_epochs=N_EPOCHS, batch_size=BATCH_SIZE)
    # output_grid_search(build_logsigrnn_model, param_grid)
    # output_random_search(build_logsigrnn_model, param_grid)

    # %% record learning curve

    df = pd.DataFrame(clf.history)
    df.to_csv(PATH_LEARNING_CURVE)
