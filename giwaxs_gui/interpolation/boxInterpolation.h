extern "C" double *boxInterpolation(const double *inten,
                                    const double *qx, const double *qy, int ndat,
                                    double xs, double xdel, int nx, double xhw,
                                    double ys, double ydel, int ny, double yhw);

extern "C" void deleteResult(double * result);
