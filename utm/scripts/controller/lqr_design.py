#!/usr/bin/env python

from this import d
import rospy 
import numpy as np
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from scipy.integrate import odeint
from tf.transformations import euler_from_quaternion
from std_msgs.msg import Float64

from mavros_msgs.msg import AttitudeTarget
import scipy

""" 
PSEUDOCODE
list of parameters for Q,R, pitch authority:
What Q,R and pitch authorities to set to?

while not recording or no input:
    - set params
    
    - if record = True 
        - start logging/recording 
    
    - if record done = True
        - when stabilized or I tell to stop then stop recording
    
    - if done_sim = True:
        break while
        
    - set next params
    
Set a list of Q and R Params

"""

Ix = 8.1 * 1E-3 #kg/m"^2
Iy = 8.1 * 1E-3 #kg/m"^2
g = 9.81 #m^2/s
m = 1.0 #kg

class LQR():
    def __init__(self, A = None, B = None, Q = None, R = None, x0 = None,
                 rate_val = None):     
        if(A is None or B is None):
            raise ValueError("Set proper system dynamics.")

        # 
        self.n = A.shape[0]
        self.m = B.shape[1]
        
        self.A = A
        self.B = 0 if B is None else B
        
        self.Q = np.diag(np.full(4,0.01))#np.diag(np.array(Q)) #if Q is None else Q
        self.Q[0,0] = 0.8   #Q = 1.0 for apriltag , Q = 3.25 for position 
        
        #self.R = np.eye(self.n) if R is None else R,20, 4,5
        self.R = np.diag([30]) # 30 for apriltag, 9.1 for regular position
        self.x = np.zeros((self.n, 1)) if x0 is None else x0
        
        #gains
        self.K = []
        
        #desired states
        self.z = [0] * len(Q)
        self.error = [0] * len(Q)
        self.lqr_output = [0] * len(Q)

        #rate values
        self.rate_val = 30 if rate_val is None else rate_val
        self.dt = 1/self.rate_val
        
    def current_state(self, x_state):
        """update position estimate """
        self.x[0] = x_state[0]
        self.x[1] = x_state[1]
        self.x[2] = x_state[2]
        self.x[3] = x_state[3]
                
    def desired_state(self, desired_val):
        """get desired position from current position"""
        #desired_x = msg.pose.position.x # - self.x[0]
        #des_y = msg.pose.position.y
        #des_vel_x = (desired_x - self.z[0])/self.dt 
        self.z[0] = desired_val[0] 
        self.z[1] = desired_val[1]
        self.z[2] = desired_val[2] #self.x[2]#desired_val[2]
        self.z[3] = desired_val[3]

    def compute_error(self):
        """compute error of state"""
        #self.error[0] = self.z[0] # - self.x[0] if not using apriltag use this
        self.error[0] = self.z[0] #- self.x[0]
        self.error[1] = self.z[1] #- self.x[1]
        self.error[2] = self.z[2] #- self.x[2]
        self.error[3] = self.z[3] #- self.x[3]
        
    def lqr(self, A, B, Q, R):
        """Solve the continuous time lqr controller.
        dx/dt = A x + B u
        cost = integral x.T*Q*x + u.T*R*u
        """
        # http://www.mwm.im/lqr-controllers-with-python/
        # ref Bertsekas, p.151

        # first, try to solve the ricatti equation, X is n x n
        X = np.matrix(scipy.linalg.solve_continuous_are(A, B, Q, R))

        # compute the LQR gain Compute $K=R^-1B^TS$
        K = np.matrix(scipy.linalg.inv(R) * (B.T * X))
        print("K values are", K)
        
        #gives solution that yields stable system, negative values
        eigVals, eigVecs = scipy.linalg.eig(A - B * K)
        return np.asarray(K), np.asarray(X), np.asarray(eigVals)

    def compute_K(self):
        """get gains from LQR"""
        #print(self.Q)
        K, _, _ = self.lqr(self.A, self.B, self.Q, self.R)
        self.K = K
        
    def update_state(self): 
        """update state space"""
        self.lqr_output = np.dot(self.B.T, self.u)
        self.x = np.dot(self.A, self.x)  + self.lqr_output
        
    def get_u(self):
        """compute controller input"""
        self.u = np.multiply(self.K, self.error)[0]
        
        max_pitch_rate = 0.25# 0.25, is the moveabout 20 degrees
        att_rate_idx = 2
        if abs(self.u[att_rate_idx])>= max_pitch_rate:
            if self.u[att_rate_idx] > 0:              
                self.u[att_rate_idx] = max_pitch_rate
            else:
                self.u[att_rate_idx] = -max_pitch_rate
                
        max_vel = 15.0
        vel_idx = 0
        if abs(self.u[vel_idx])>= max_vel:
            if self.u[vel_idx] > 0:              
                self.u[vel_idx] = max_vel
            else:
                self.u[vel_idx] = -max_vel

    def main(self):         
        """update values to LQR"""
        self.compute_error()
        # self.compute_K()
        self.get_u()
        self.update_state()
        
class DroneLQR():
    def __init__(self, Ax, Bx, Ay, By, Q, R, rate_val):
        """drone LQR controller"""
        #quad position callback
        self.quad_sub = rospy.Subscriber("uav0/mavros/odometry/in",
                                         Odometry,
                                         self.current_state)
        
        self.track_sub = rospy.Subscriber("uav0/mavros/vision_pose/pose", 
                                                 PoseStamped,
                                                 self.desired_state)
        
        self.k_pub = rospy.Publisher("K_gain", LQRGain, queue_size=5)
        
        self.x_state = np.array([0.0,0.0,0.0,0.0])
        self.y_state = np.array([0.0,0.0,0.0,0.0])      
        
        #subsystem lqr X
        self.x_lqr = LQR(A = Ax, B = Bx, Q = Q, R = R, x0 = self.x_state,
                    rate_val = rate_val) #import matrices into class
        #subsystem lqr Y
        self.y_lqr = LQR(A = Ay, B = By, Q = Q, R = R, x0 = None,
                    rate_val = rate_val) #import matrices into class

        #intialize desired states
        self.desired_x = [0.0, 0.0, 0.0, 0.0]
        self.desired_y = [0.0, 0.0, 0.0, 0.0]
        self.dt = 1/rate_val
        
    def current_state(self, msg):
        """update current estimates"""
        px = msg.pose.pose.position.x 
        py = msg.pose.pose.position.y
        
        vel_x = msg.twist.twist.linear.x
        vel_y = msg.twist.twist.linear.y
        
        orientation_q = msg.pose.pose.orientation
        orientation_list = [orientation_q.x, orientation_q.y,
                             orientation_q.z, orientation_q.w]
        (roll, pitch, yaw) = euler_from_quaternion(orientation_list)
        pitch_rate = pitch - self.x_state[2]/self.dt
        roll_rate = roll - self.y_state[2]/self.dt
         
        self.x_state[0] = px
        self.x_state[1] = vel_x
        self.x_state[2] = pitch
        self.x_state[3] = pitch_rate

        self.y_state[0] = py
        self.y_state[1] = vel_y
        self.y_state[2] = roll
        self.y_state[3] = roll_rate

    def desired_state(self, msg):
        """get desired position from current position"""
        desired_x = msg.pose.position.x # - self.x[0]
        desired_y = msg.pose.position.y
        
        #print("desired x and desired y", desired_x, desired_y)
        self.desired_x[0] = desired_x
        self.desired_y[0] = desired_y
        
        self.desired_x[2] = desired_x - self.x_state[2]
        self.desired_y[2] = desired_y - self.y_state[2]

    def publish_input(self):
        """publish body rate commands"""
        # gains = LQRGain()        
        tol = 0.25    #0.075 for regular tracking , 0.5 for apriltag
        zero_vals = [0,0,0,0]
        input_x = [float(xu) for xu in self.x_lqr.u]
        input_y = [-float(yu) for yu in self.y_lqr.u]
        
        # input_x_half = [float(xu)/2 for xu in self.x_lqr.u]
        # input_y_half= [-float(yu)/2 for yu in self.y_lqr.u]
        #print("rate command is", input_x[2])
        
        if abs(self.x_lqr.error[0]) <= tol and abs(self.y_lqr.error[0]) >= tol:
            pub_vals = zero_vals
            pub_vals.extend(input_y)
            self.k_pub.publish(pub_vals)
            #self.k_pub.publish([0.0, -self.y_lqr.u])
            
        elif abs(self.x_lqr.error[0]) >= tol and abs(self.y_lqr.error[0]) <= tol:
            pub_vals = input_x
            pub_vals.extend(zero_vals)
            self.k_pub.publish(pub_vals)
            #self.k_pub.publish([self.x_lqr.u, 0.0])
        
        elif abs(self.x_lqr.error[0]) <= tol and abs(self.y_lqr.error[0]) <= tol:
            pub_vals = zero_vals
            pub_vals.extend(zero_vals)
            self.k_pub.publish(pub_vals)
            #self.k_pub.publish([0.0, 0.0])
        else:
            pub_vals = input_x
            pub_vals.extend(input_y)   
            print("publishing values", input_x)
            self.k_pub.publish(pub_vals)

    def compute_gains(self):
        """get gains from ricatti equation"""
        self.x_lqr.compute_K()
        self.y_lqr.compute_K()
        
    def main(self):
        """main implementation"""
        self.x_lqr.current_state(self.x_state)
        self.x_lqr.desired_state(self.desired_x)
        
        self.y_lqr.current_state(self.y_state)
        self.y_lqr.desired_state(self.desired_y)
        
        self.x_lqr.main()
        self.y_lqr.main()
        
        self.publish_input()
        
        
if __name__ == "__main__":
    
    #rospy.init_node("lqr_controller", anonymous=False)
    rate_val = 30

    ############ Set up X and Y #####################
    # X-subsystem
    # The state variables are x, dot_x, pitch, dot_pitch
    Ax = np.array(
        [[0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, g, 0.0],
        [0.0, 0.0, 0.0, 1.0],
        [0.0, 0.0, 0.0, 0.0]])
    
    Bx = np.array(
        [[0.0],
        [0.0],
        [0.0],
        [1 / Ix]])
    
    # Y-subsystem
    # The state variables are y, dot_y, roll, dot_roll
    Ay = np.array(
        [[0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, -g, 0.0],
        [0.0, 0.0, 0.0, 1.0],
        [0.0, 0.0, 0.0, 0.0]])
    
    By = np.array(
        [[0.0],
        [0.0],
        [0.0],
        [1 / Iy]])
    
    ## Q penalty
    Q_fact =  1.5 #penalizes performance rating 
    Q = np.array([[Q_fact, 0, 0], 
                [0, Q_fact, 0, 0], 
                [0, 0, Q_fact/2, 0], 
                [0, 0 , 0, Q_fact/2]])
    
    ## R penalty for input
    R = np.array([[Q_fact, 0, 0], 
                [0, Q_fact, 0, 0], 
                [0, 0, Q_fact/2, 0], 
                [0, 0 , 0, Q_fact/2]])
    
    # lqr = LQR(A = Ax, B = Bx, Q = Q, R = R, x0 = None,
    #              rate_val = rate_val) #import matrices into class

    drone_lqr = lqr.DroneLQR(Ax, Bx, Ay, By, Q, R, rate_val)
    drone_lqr.compute_gains()
    # rate = rospy.Rate(rate_val)
    # while not rospy.is_shutdown():
    #     drone_lqr.main()
    #     rate.sleep()
    
    
    
    