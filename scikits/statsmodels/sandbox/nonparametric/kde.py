"""
Univariate Kernel Density Estimators

References
----------
Racine, Jeff. (2008) "Nonparametric Econometrics: A Primer," Foundation and
    Trends in Econometrics: Vol 3: No 1, pp1-88.
    http://dx.doi.org/10.1561/0800000009

http://en.wikipedia.org/wiki/Kernel_%28statistics%29

Silverman, B.W.  Density Estimation for Statistics and Data Anaylsis.
"""
import numpy as np
import bandwidths #TODO: change to absolute import


#### Convenience Functions to be moved to kerneltools ####

def forrt(X,m=None):
    """
    RFFT with order like Munro (1976) FORTT routine.
    """
    if m is None:
        m = len(X)
    y = np.fft.rfft(X,m)/m
    return np.r_[y.real,y[1:-1].imag]

def revrt(X,m=None):
    """
    Inverse of forrt. Equivalent to Munro (1976) REVRT routine.
    """
    if m is None:
        m = len(X)
    y = X[:m/2+1] + np.r_[0,X[m/2+1:],0]*1j
    return np.fft.irfft(y)*m

def silverman_transform(X, bw, RANGE):
    """
    Transform density estimate (Gaussian Kernel only) according to Silverman AS 176.

    Notes
    -----
    Underflow is intentional as a dampener.
    """
    M = len(X)
    J = np.arange(M/2+1)
    FAC1 = 2*(np.pi*bw/RANGE)**2
    JFAC = J**2*FAC1
    BC = 1 - 1./3 * (J*1./M*np.pi)**2
    FAC = np.exp(-JFAC)/BC
    SMOOTH = np.r_[FAC,FAC[1:-1]] * X
    return SMOOTH

def linbin(X,a,b,M, trunc=1):
    """
    Linear Binning as described in Fan and Marron (1994)
    """
    gcnts = np.zeros(M)
    delta = (b-a)/(M-1)

    for x in X:
        lxi = ((x - a)/delta) # +1
        li = int(lxi)
        rem = lxi - li
        if li > 1 and li < M:
            gcnts[li] = gcnts[li] + 1-rem
            gcnts[li+1] = gcnts[li+1] + rem
        if li > M and trunc == 0:
            gcnts[M] = gncts[M] + 1

    return gcnts

def counts(x,v):
    """
    Counts the number of elements of x that fall within v

    Notes
    -----
    Using np.digitize and np.bincount
    """
    idx = np.digitize(x,v)
    try: # numpy 1.6
        return np.bincount(idx, minlength=len(v))
    except:
        bc = np.bincount(idx)
        return np.r_[bc,np.zeros(len(v)-len(bc))]


def kdesum(x,axis=0):
    return np.asarray([np.sum(x[i] - x, axis) for i in range(len(x))])

# global dict?
bandwidth_funcs = dict(scott=bandwidths.bw_scott,silverman=bandwidths.bw_silverman)

def select_bandwidth(X, bw, kernel):
    """
    Selects bandwidth
    """
    bw = bw.lower()
    if bw not in ["scott","silverman"]:
        raise ValueError("Bandwidth %s not understood" % bw)
    if kernel == "gauss":
        return bandwidth_funcs[bw](X)
    else:
        raise ValueError("Only Gaussian Kernels are currently supported")


#### Kernel Density Estimators ####

def kdensity(X, kernel="gauss", bw=None, weights=None, gridsize=None, axis=0,
        clip=(-np.inf,np.inf), cut=3, retgrid=True):
    """
    Rosenblatz-Parzen univariate kernel desnity estimator

    Parameters
    ----------
    X : array-like
    kernel : str
        "bi" for biweight
        "cos" for cosine
        "epa" for Epanechnikov, default
        "epa2" for alternative Epanechnikov
        "gauss" for Gaussian.
        "par" for Parzen
        "rect" for rectangular
        "tri" for triangular
    bw : str, int
        If None, the bandwidth uses the rule of thumb for the given kernel.
        ie., h = c*nobs**(-1/5.) where c = (see Racine 2.6)
        gridsize : int
        If gridsize is None, min(len(X), 512) is used.  Note that this number
        is rounded up to the next highest power of 2.

    Notes
    -----
    Weights aren't implemented yet.
    Does not use FFT.
    Should actually only work for 1 column.
    """
    X = np.asarray(X)
    if X.ndim == 1:
        X = X[:,None]
    X = X[np.logical_and(X>clip[0], X<clip[1])] # won't work for two columns.
                                                # will affect underlying data?
    nobs = float(len(X)) # after trim

    # if bw is None, select optimal bandwidth for kernel
    if bw == None:
        if kernel.lower() == "gauss":
            c = 1.0592 * np.std(X, axis=axis, ddof=1)
        if kernel.lower() == "epa":
            c = 1.0487 * np.std(X, axis=axis, ddof=1) # is this correct?
#TODO: can use windows from scipy.signal?
        h = c * nobs**(-1/5.)
    else:
        h = bw

    if gridsize == None:
        gridsize = np.max((nobs,512.))
    # round gridsize up to the next power of 2
    gridsize = 2**np.ceil(np.log2(gridsize))
    # define mesh
    grid = np.linspace(np.min(X,axis) - cut*bw,np.max(X,axis)+cut*bw,gridsize)
    # this will fail for not 1 column
    if grid.ndim == 1:
        grid = grid[:,None]

    k = (X.T - grid)/h  # uses broadcasting
# res = np.repeat(x,n).reshape(m,n).T - np.repeat(xi,m).reshape(n,m))/h
    if kernel.lower() == "epa":
        k = np.zeros_like(grid) + np.less_equal(np.abs(k),
                np.sqrt(5)) * 3/(4*np.sqrt(5)) * (1-.2*k**2)
#        k = (.15/np.sqrt(5))*(5-k**2)/h
#        k[k<0] = 0
    if kernel.lower() == "gauss":
        k = 1/np.sqrt(2*np.pi)*np.exp(-.5*k**2)
#        k = np.clip(k,1e12,0)
#TODO:
    if weights == None:
        q = nobs
        q = 1
        weights = 1
    if retgrid:
        return np.mean(1/(q*h)*weights*k,1),k/(q*h)*weights, grid
    else:
        return np.mean(1/(q*h)*weights*k,1),k/(q*h)*weights
#TODO: need to check this
#    return k.mean(1),k

def kdensityfft(X, kernel="gauss", bw="scott", adjust=1, weights=None, gridsize=None,
        clip=(-np.inf,np.inf), cut=3, retgrid=True):
    """
    Rosenblatz-Parzen univariate kernel desnity estimator

    Parameters
    ----------
    X : array-like
    kernel : str
        "bi" for biweight
        "cos" for cosine
        "epa" for Epanechnikov, default
        "epa2" for alternative Epanechnikov
        "gauss" for Gaussian.
        "par" for Parzen
        "rect" for rectangular
        "tri" for triangular
        ONLY GAUSSIAN IS CURRENTLY IMPLEMENTED.
    bw : str, float
        "scott" - 1.059 * A * nobs ** (-1/5.), where A is min(std(X),IQR/1.34)
        "silverman" - .9 * A * nobs ** (-1/5.), where A is min(std(X),IQR/1.34)
        If a float is given, it is the bandwidth.
    adjust : float
        An adjustment factor for the bw. Bandwidth becomes bw * adjust.
    gridsize : int
        If gridsize is None, min(len(X), 512) is used.  Note that this number
        is rounded up to the next highest power of 2.
    cut : float
        Defines the length of the grid past the lowest and highest values of X so that
        the kernel goes to zero. The end points are -/+ cut*bw*{X.min() or X.max()}

    Notes
    -----
    Only the default kernel is implemented.
    Weights aren't implemented yet.
    Uses FFT.
    Should only work for 1 column for now
    """
    X = np.asarray(X)
    X = X[np.logical_and(X>clip[0], X<clip[1])] # won't work for two columns.
                                                # will affect underlying data?
    try:
        bw = float(bw)
    except:
        bw = select_bandwidth(X, bw, kernel) # will cross-val fit this pattern?
    bw *= adjust

    nobs = float(len(X)) # after trim

    # 1 Make grid and discretize the data
    if gridsize == None:
        gridsize = np.max((nobs,512.))
    gridsize = 2**np.ceil(np.log2(gridsize)) # round to next power of 2

    a = np.min(X)-cut*bw
    b = np.max(X)+cut*bw
    grid,delta = np.linspace(a,b,gridsize,retstep=True)
    RANGE = b-a

# This is the Silverman binning function, but I believe it's buggy (SS)

# weighting according to Silverman
#    count = counts(X,grid)
#    binned = np.zeros_like(grid)    #xi_{k} in Silverman
#    j = 0
#    for k in range(int(gridsize-1)):
#        if count[k]>0: # there are points of X in the grid here
#            Xingrid = X[j:j+count[k]] # get all these points
#            # get weights at grid[k],grid[k+1]
#            binned[k] += np.sum(grid[k+1]-Xingrid)
#            binned[k+1] += np.sum(Xingrid-grid[k])
#            j += count[k]
#    binned /= (nobs)*delta**2 # normalize binned to sum to 1/delta

#NOTE: THE ABOVE IS WRONG, JUST TRY WITH LINEAR BINNING
    binned = linbin(X,a,b,gridsize)/(delta*nobs)

    # step 2 compute FFT of the weights, using Munro (1976) FFT convention
    y = forrt(binned)

    # step 3 and 4 for optimal bw compute zstar and the density estimate f
    # don't have to redo the above if just changing bw, ie., for cross val

#NOTE: I believe this is kernel specific, so needs to be replaced for generality
    zstar = silverman_transform(y, bw, RANGE)
    f = revrt(zstar)
    if retgrid:
        return f, grid
    else:
        return f

if __name__ == "__main__":
    import numpy as np
    np.random.seed(12345)
    xi = np.random.randn(100)
    f,k,grid = kdensity(xi, kernel="gauss", bw=.372735, retgrid=True)
    f2 = kdensityfft(xi, kernel="gauss", bw="silverman",retgrid=False)

# do some checking vs. silverman algo.
# you need denes.f, http://lib.stat.cmu.edu/apstat/176
#NOTE: I (SS) made some changes to the Fortran
# and the FFT stuff from Munro http://lib.stat.cmu.edu/apstat/97o
# then compile everything and link to denest with f2py
#Make pyf file as usual, then compile shared object
#f2py denest.f -m denest2 -h denest.pyf
#edit pyf
#-c flag makes it available to other programs, fPIC builds a shared library
#/usr/bin/gfortran -Wall -c -fPIC fft.f
#f2py -c denest.pyf ./fft.o denest.f

    try:
        from denest2 import denest
        a = -3.4884382032045504
        b = 4.3671504686785605
        RANGE = b - a
        bw = bandwidths.bw_silverman(xi)

        ft,smooth,ifault,weights,smooth1 = denest(xi,a,b,bw,np.zeros(512),np.zeros(512),0,
                np.zeros(512), np.zeros(512))
# We use a different binning algo, so only accurate up to 3 decimal places
        np.testing.assert_almost_equal(f2, smooth, 3)
#NOTE: for debugging
#        y2 = forrt(weights)
#        RJ = np.arange(512/2+1)
#        FAC1 = 2*(np.pi*bw/RANGE)**2
#        RJFAC = RJ**2*FAC1
#        BC = 1 - RJFAC/(6*(bw/((b-a)/M))**2)
#        FAC = np.exp(-RJFAC)/BC
#        SMOOTH = np.r_[FAC,FAC[1:-1]] * y2

#        dens = revrt(SMOOTH)

    except:
#        ft = np.loadtxt('./ft_silver.csv')
#        smooth = np.loadtxt('./smooth_silver.csv')
        print "Didn't get the estimates from the Silverman algorithm"
