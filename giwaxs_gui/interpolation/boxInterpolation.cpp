#include "boxInterpolation.h"
#include <cmath>

void deleteResult(double * result){
    delete[] result;
}

inline void getind(double xmsdel, double hwdel, int n, int &imin,
                   int &imax);

double *boxInterpolation(const double *inten,
                         const double *qx, const double *qy, int ndat,
                         double xs, double xdel, int nx, double xhw,
                         double ys, double ydel, int ny, double yhw) {
    int ximin, ximax, yimin, yimax;
    int i, k, l, ind;
    int size = nx * ny;
    double xmsdel;

    auto *ninten = new int[size];
    auto *ginten = new double[size];

    double xhwdel = xhw / 2. / xdel;
    double yhwdel = yhw / 2./ ydel;

    for (i = 0; i < size; i++) {
        ginten[i] = 0;
        ninten[i] = 0;
    }
    for (i = 0; i < ndat; i++) {
        xmsdel = (qx[i] - xs) / xdel;
        getind(xmsdel, xhwdel, nx, ximin, ximax);
        xmsdel = (qy[i] - ys) / ydel;
        getind(xmsdel, yhwdel, ny, yimin, yimax);

        for (l = ximin; l <= ximax; l++) {
            for (k = yimin; k <= yimax; k++) {
                ind = l * ny + k;
                ninten[ind] += 1;
                ginten[ind] += inten[i];

            }
        }
    }
    for (i = 0; i < size; i++) {
        if (ninten[i] != 0)
            ginten[i] = ginten[i] / (double) ninten[i];
    }
    delete[] ninten;
    return ginten;
}

inline void getind(double xmsdel, double hwdel, int n, int &imin,
                   int &imax) {
    imin = ceil(xmsdel - hwdel);
    if (imin < 0) imin = 0;
    if (imin > (n - 1)) imin = n;
    imax = floor(xmsdel + hwdel);
    if (imax < 0) imax = -1;
    if (imax > (n - 1)) imax = n - 1;
}
