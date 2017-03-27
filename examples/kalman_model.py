import asyncio
import numpy as np
from sklearn import linear_model

# For Kalman filtering
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise

from thingflow.base import OutputThing, InputThing, from_iterable, Scheduler

class SGDLinearRegressionModel(OutputThing, InputThing):
    def __init__(self):
        OutputThing.__init__(self, ports=['train', 'observe', 'predict'])
        self.clf = linear_model.SGDRegressor()

    def on_train_next(self, x):
        print("On train next called")
        # training input: train the model
        xx = np.asarray(x[0])
        yy = np.asarray(x[1])
        self.clf.partial_fit(xx, yy) 

    def on_train_error(self, x):
        print("On train error called")
        self.on_error(x)

    def on_train_completed(self):
        print("On train completed called")
        self.on_completed()

    def on_observe_next(self, x):
        print("On observe next called")
        xx = np.asarray(x)
        p = self.clf.predict(xx)
        self._dispatch_next(p, port='predict')
    def on_observe_error(self, x):
        self.on_error(x)
    def on_observe_completed(self):
        self.on_completed()

class FilterModel(OutputThing, InputThing):
    def __init__(self, filter):
        OutputThing.__init__(self, ports=['observe', 'predict'])
        self.filter = filter

    def on_observe_next(self, measurement):
        print("On observerain next called")
        # training input: train the model
        self.filter.predict()
        self.filter.update(measurement)
        self._dispatch_next(self.filter.x, port='predict')

    def on_observe_error(self, x):
        print("On observe error called")
        self.on_error(x)

    def on_observe_completed(self):
        print("On observe completed called")
        self.on_completed()


class KalmanFilterModel(FilterModel):
    """Implements Kalman filters using filterpy.
          x' = Fx + Bu + w
          y  = H x + ww
    """
    def __init__(self, dim_state, dim_control, dim_measurement, 
                 initial_state_mean, initial_state_covariance, 
                 matrix_F, matrix_B, 
                 process_noise_Q,
                 matrix_H, measurement_noise_R):
        filter = KalmanFilter(dim_x=dim_state, dim_u=dim_control, dim_z=dim_measurement)
        filter.x = initial_state_mean
        filter.P = initial_state_covariance

        filter.Q = process_noise_Q

        filter.F = matrix_F
        filter.B = matrix_B
        filter.H = matrix_H

        filter.R = measurement_noise_R # covariance matrix
        super().__init__(filter)
        


def main_linear():
    obs_stream = from_iterable(iter([ [ [ [1.0, 1.0], [2.0, 2.0]], [1.0, 2.0] ], [  [ [6.0, 6.0], [9.0, 9.0]], [6.0, 9.0] ]  ]))
    pred_stream = from_iterable(iter([ [3.0, 3.0] ]))
    model = SGDLinearRegressionModel()
    obs_stream.connect(model, port_mapping=('default', 'train'))
    obs_stream.connect(print)

    pred_stream.connect(model, port_mapping=('default', 'observe'))
    model.connect(print, port_mapping=('predict', 'default'))
    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_periodic(obs_stream, 1)
    scheduler.schedule_periodic(pred_stream, 5)
    scheduler.run_forever()

def main_kalman():
    dim_x = 2
    dim_u = 1
    dim_z = 1
    initial_state_mean = np.array([ [1.0] , [0.0] ])
    initial_state_covariance = 1000 * np.eye(dim_x)

    F = np.array([  [ 1., 1.], [0., 1.] ])
    B  = np.zeros((2, 1) )
    Q = Q_discrete_white_noise(dim=2, dt=0.1, var=0.13)

    H = np.array([[1.,0.]])
    R = 5 * np.eye(1) 
    
    model = KalmanFilterModel(dim_x, dim_u, dim_z, initial_state_mean, initial_state_covariance, 
                              F, B, Q, H, R)
    measurement_stream = from_iterable(iter([ [ 1.0 ], [0.0] ]))
    # measurement_stream = from_iterable(iter([ np.array([ [1.0, 1.0] ]) ]))
    measurement_stream.connect(model, port_mapping=('default', 'observe'))
    model.connect(print, port_mapping=('predict', 'default'))

    scheduler = Scheduler(asyncio.get_event_loop())
    scheduler.schedule_periodic(measurement_stream, 1)
    scheduler.run_forever()


def main():
    main_kalman()

if __name__ == '__main__':
    main()
