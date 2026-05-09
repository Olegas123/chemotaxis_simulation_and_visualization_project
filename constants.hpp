#ifndef CONSTANTS_HPP
#define CONSTANTS_HPP

#include <cmath>

const double D_U = 0.1;
const double D_W = 0.2;
const double CHI = 8.3;
const double ALPHA = 1.0;
const double BETA = 0.73;
const double GAMMA = 0.025;

const double W_0 = 1.0;

const double R = 5.0;            // Cylinder/disk radius
const double H = 10.0;           // Cylinder height
const int N_RHO = 40;            // Number of radial points (polar coordinate)
const int N_PHI = 224;           // Number of angular points (around circle/cylinder)
const int NZ = 80;               // Number of vertical points (height direction)

const double L_1D = 2.0 * M_PI * R;
const double DX_1D = L_1D / N_PHI;

// Polar coordinates (r, phi)
const double D_RHO = R / N_RHO;               // Radial step
const double D_PHI = 2.0 * M_PI / N_PHI;      // Angular step

// Cylindrical surface (phi, z)
const double L_CYL = 2.0 * M_PI * R;          // Circumference
const double DX_CYL = L_CYL / N_PHI;          // Angular step
const double DZ = H / NZ;                     // Vertical step

const double T_FINAL = 400;
const double DT_1D = 0.00005;
const double DT_2D_POLAR = 0.00005;
const double DT_2D_CYL = 0.00005;
const double DT_2D_COMBINED = 0.00005;
const double DT_3D = 0.00005;

// Save snapshots at these time intervals (in simulation time units)
const double SAVE_EVERY_T_1D = 50.0;
const double SAVE_EVERY_T_2D_POLAR = 1.0;
const double SAVE_EVERY_T_2D_CYL = 1.0;
const double SAVE_EVERY_T_2D_COMBINED = 1.0;
const double SAVE_EVERY_T_3D = 1.0;

// Progress reporting (in simulation time units)
const double PROGRESS_EVERY_T = 50;

// Number of spatiotemporal samples (evenly distributed over T_FINAL)
const int SPATIOTEMPORAL_SAMPLES = 1600;

// 2D polar: average over radial indices near outer edge
const int RHO_START = N_RHO - 6;
const int RHO_END = N_RHO - 3;

// 2D cylindrical: average over vertical indices near bottom
const int Z_START_2D = NZ - 5;
const int Z_END_2D = NZ - 2;

// 3D: average over radial and vertical indices
const int RHO_START_3D = N_RHO - 6;
const int RHO_END_3D = N_RHO - 3;
const int Z_START_3D = NZ - 5;
const int Z_END_3D = NZ - 2;

// Angular coarsening thresholds
const int RHO_HALF = N_RHO / 2;
const int RHO_QUARTER = N_RHO / 4;

// Should be fine tuned for each specific cpu (omp_get_max_threads() might not work due to overhead)
// Also, might not work as expected on small grid sizes due to overhead
const int OPEN_MP_THREAD_COUNT = 1;

#endif // CONSTANTS_HPP