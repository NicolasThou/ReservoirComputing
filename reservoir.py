import numpy as np
import scipy as scp
from matplotlib import pyplot as plt
from scipy.sparse import random

"""

References :
1 - Reservoir computing approaches to recurrent neural network training - Mantas Lukoševicius, Herbert Jaeger
2 - The" echo state" approach to analysing and training recurrent neural networks-with an erratum note - Herbert Jaeger
3 - Backpropagation-Decorrelation: online recurrent learning with O(N) complexity - Jochen J. Steil

"""


def mackey_glass(N, a=0.2, b=1, c=0.9, d=17, e=10, initial=0.1):
    """
    Generate times series from the Mackey Glass equation

    Parameters:
    ==========
    N : number of sample
    a, b, c, d, e : hyper parameter
    initial : initial value of x

    Return:
    ======
    return a numpy array of length N of scalars
    """

    y = np.full(N, initial)
    y.reshape(N, 1)

    x = np.linspace(0, N, N, endpoint=False)
    x.reshape(N, 1)

    for i in range(len(y) - 1):
        y[i+1] = c * y[i] + ((a * y[i - d]) / (b + (y[i - d] ** e)))

    return y


def sinus(N):
    """
    Test on a simple signal, sinus function
    """
    x = np.arange(0, N * np.pi, 0.1)  # start,stop,step
    y = np.sin(x)
    y = np.array([y]).T

    return y


def train_test_mackey_glass_npy(N1, N2):
    """
    import the data from the .npy file

    train data from 0 to N1
    test data from N1 to N2
    """

    data = np.load('mackey-glass.npy')
    return data[:N1, np.newaxis], data[N1:N2, np.newaxis]


class Reservoir:
    """
    This class implement the Reservoir Computing or Echo State Network
    """
    def __init__(self, dim_N_x, dim_N_y, dim_N_u):
        if dim_N_y != dim_N_u:
            raise ValueError('dim_N_y has to be equal to dim_N_u')

        self.radius = 1.25
        self.leak = 0.5
        self.warmup = 100

        self.dim_N_x = dim_N_x
        self.dim_N_y = dim_N_y
        self.dim_N_u = dim_N_u

        # Matrix
        self.weight_in = np.random.uniform(-0.5, 0.5, (self.dim_N_x, self.dim_N_u))
        self.weight_out = np.random.uniform(-0.5, 0.5, (self.dim_N_y, self.dim_N_x))  # the only weights updated
        # 100% of values are different to 0
        self.weight = np.random.uniform(-0.5, 0.5, (self.dim_N_x, self.dim_N_x))
        self.weight *= np.random.uniform(0, 1, (self.dim_N_x, self.dim_N_x)) < 1
        self.weight *= self.radius/np.max(np.abs(np.linalg.eigvals(self.weight)))

        # Initialization at n = 0
        self.input = 0
        self.output = self.input  # y(0)
        self.internal = np.random.uniform(-1, 1, self.dim_N_x)

    def training_set(self, N):
        """
        Split the time series into a list of input (u(0), u(1), ..., u(n))

        return ndarray of sample
        """

        time_serie = mackey_glass(N=N, a=0.2, b=1, c=0.9, d=23, e=10, initial=0.1)

        # size of the time serie / self.dim_N_u = number of sample
        # sample of size dim_N_u
        X_set = np.split(time_serie, N/self.dim_N_u)
        X_set = np.array(X_set)

        return X_set

    def forward_input(self):
        """
        return : W_in . u(n)
        """

        return self.weight_in @ self.input

    def forward_internal(self):
        """
        return : W . x(n-1)
        """

        return self.weight @ self.internal

    def forward(self):
        """
        return x(n)

        Equation : tanh(W_in.u(n) + W.x(n-1) + bias)
        """

        a = self.forward_input()
        b = self.forward_internal()

        return np.tanh(a + b)

    def forward_out(self):
        """
        Compute W_out . x(n)
        return y(n)
        """
        return np.dot(self.weight_out, self.internal)

    def update(self, x, y):
        """
        Update the weight matrix W_out

        Parameter :
        =========
        ground truth = y(n)

        Return the new weight out Matrix where we start with the equation W_out.X = Y
        such that X is the internal state matrix

        Exemple:
        =======
        900 samples
        1000 feature for x
        1 output for y

        x shape (900, 1000)
        y shape (900, 1)

        W_out shape (dim_Y, dim_X) = (1, 1000)
        """

        x = np.transpose(x)
        y = np.transpose(y)
        new_W_out = (y @ x.T) @ np.linalg.inv(x @ x.T + 1e-8 * np.eye(self.dim_N_x))
        print(np.shape(new_W_out))

        return new_W_out

    def training_testing(self, n1, n2):
        """
        ** Description :

        use the forward functions to have the reccurent loop and then update the W_out matrix

        ** Teacher Forcing :

        For the first n iteration :
        using the actual or expected output from the training dataset at the current time step y(t)
        as input in the next time step X(t+1), rather than the output generated by the network.

        ** Updating:

        Update W_out after recording every internal state and every input (ground truth)

        Arg:
        ===
        train data from 0 to N1 (.npy file)
        test data from N1 to N2 (.npy file). The test data has length equal to N2.

        """
        # initialization
        #train = self.training_set(2000)
        #train = sinus(2000)
        train, test = train_test_mackey_glass_npy(n1, n2)
        self.input = train[0]
        reservoir_state, input_signal = [], []

        # Warmup and saving
        for i in range(n1-1):
            self.internal = (1 - self.leak) * self.internal + self.leak * self.forward()  # X vector (in reservoir)
            self.internal[0] = 1  # bias
            if i >= self.warmup:
                reservoir_state.append(self.internal)  # X vector
                input_signal.append(self.input)  # Y vector

            # Teacher Forcing
            self.input = train[i+1]

        # update the weight out matrix
        self.weight_out = self.update(reservoir_state, input_signal)

        # testing
        result, signal = [], []
        self.input = test[0]  # train[0] for sinus
        for i in range(n2-n1):  # range(n1, n2) for sinus
            self.internal = (1 - self.leak) * self.internal + self.leak * self.forward()
            self.internal[0] = 1  # bias
            self.output = self.forward_out()  # prediction
            result.append(self.output[0])
            signal.append(test[i][0])  # train[i][0] for sinus

            # link the output to the input
            self.input = self.output

        return signal, result


def plot(n1, n2, signal, prediction):

    x = np.linspace(n1, n2, n2-n1, endpoint=False)
    x.reshape(n2-n1, 1)

    plt.figure()
    plt.plot(x, signal, label='signal', color='y')
    # Place a legend to the right of this smaller subplot.
    #plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    #plt.show()
    #plt.close()

    #plt.figure()
    plt.plot(x, prediction, label='prediction', color='r')
    # Place a legend to the right of this smaller subplot.
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    plt.show()
    plt.close()


if __name__ == '__main__':

    # dim_N_x, dim_N_y, dim_N_u
    r = Reservoir(1000, 1, 1)

    # training for 900 iterations, warmup 100 iteration, test 300 iterations
    pred, x = r.training_testing(1000, 1300)

    plot(1000, 1300, pred[:300], x[:300])







