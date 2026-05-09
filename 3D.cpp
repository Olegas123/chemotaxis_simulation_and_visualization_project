#include "constants.hpp"
#include "writer.hpp"
#include "initialConditions.hpp"
#include "sim_init.hpp"
#include "sim_helpers.hpp"
#include <iostream>
#include <fstream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>
#include <iomanip>
#include <limits>
#include <ctime>

#ifdef _OPENMP
#include <omp.h>
#endif

using std::vector;
using std::max, std::min;

struct RhoInfo {
    double rho_i;
    double inv_rho_i;
    double inv_rho_i_sq;
    double rho_plus_half;
    double rho_minus_half;
};

void initializeRandom(vector<vector<vector<double>>>& field, double mean, double stddev) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::normal_distribution<double> dist(mean, stddev);
    
    for (int r = 0; r < N_RHO; ++r) {
        for (int p = 0; p < N_PHI; ++p) {
            for (int z = 0; z < NZ; ++z) {
                field[r][p][z] = std::max(0.0, dist(gen));
            }
        }
    }
}

bool checkForNaN(const vector<vector<vector<double>>>& u,
                const vector<vector<vector<double>>>& v,
                const vector<vector<vector<double>>>& w,
                int step, double t) {
    bool has_nan = false;
    
    #pragma omp parallel for collapse(3) reduction(||:has_nan)
    for (int r = 0; r < N_RHO; ++r) {
        for (int p = 0; p < N_PHI; ++p) {
            for (int z = 0; z < NZ; ++z) {
                if (std::isnan(u[r][p][z]) || std::isnan(v[r][p][z]) || std::isnan(w[r][p][z])) {
                    has_nan = true;
                }
            }
        }
    }
    
    if (has_nan) {
        std::cerr << "\n!!! NaN detected at step " << step << " (t=" << t << ") !!!\n";
        std::cerr << "Simulation is terminating to prevent further corruption.\n";
    }
    
    return has_nan;
}

int main(int argc, char* argv[]) {
    std::cout << std::fixed << std::setprecision(6);
    SIM_INIT(argc, argv, DT_3D, SAVE_EVERY_T_3D);
    
    #ifdef _OPENMP
    omp_set_num_threads(OPEN_MP_THREAD_COUNT);
    #else
    std::cout << "WARNING: OpenMP not enabled! Recompile with -fopenmp\n";
    #endif
    
    auto start_time = std::chrono::high_resolution_clock::now();
        
    vector<vector<vector<double>>> u_current(N_RHO, 
        vector<vector<double>>(N_PHI, vector<double>(NZ, 0.0)));
    vector<vector<vector<double>>> v_current(N_RHO, 
        vector<vector<double>>(N_PHI, vector<double>(NZ, 0.0)));
    vector<vector<vector<double>>> w_current(N_RHO, 
        vector<vector<double>>(N_PHI, vector<double>(NZ, W_0)));
    
    vector<vector<vector<double>>> u_next = u_current;
    vector<vector<vector<double>>> v_next = v_current;
    vector<vector<vector<double>>> w_next = w_current;
    
    auto* u_curr_ptr = &u_current;
    auto* u_next_ptr = &u_next;
    auto* v_curr_ptr = &v_current;
    auto* v_next_ptr = &v_next;
    auto* w_curr_ptr = &w_current;
    auto* w_next_ptr = &w_next;
    
    vector<vector<double>> spatiotemporal_data;
    spatiotemporal_data.reserve(SPATIOTEMPORAL_SAMPLES);
    int spatiotemporal_interval = std::max(1, n_steps / SPATIOTEMPORAL_SAMPLES);
    
    if (!ic_file.empty()) {
        std::cout << "Loading initial conditions from: " << ic_file << "\n";
        if (!load3DInitialConditions(ic_file, *u_curr_ptr, N_RHO, N_PHI, NZ)) {
            std::cerr << "Failed to load IC, using random instead\n";
            initializeRandom(*u_curr_ptr, 1.0, 0.1);
        }
    } else {
        std::cout << "No IC file provided, using random initialization\n";
        initializeRandom(*u_curr_ptr, 1.0, 0.1);
    }

    std::cout << "Init zero: " << (*u_curr_ptr)[N_RHO-1][0][NZ-1] << std::endl;
    
    vector<RhoInfo> rhoInfo(N_RHO);
    for (int r = 0; r < N_RHO; ++r) {
        rhoInfo[r].rho_i = r * D_RHO;
        if (r > 0) {
            rhoInfo[r].inv_rho_i = 1.0 / rhoInfo[r].rho_i;
            rhoInfo[r].inv_rho_i_sq = 1.0 / (rhoInfo[r].rho_i * rhoInfo[r].rho_i);
            rhoInfo[r].rho_plus_half = rhoInfo[r].rho_i + 0.5 * D_RHO;
            rhoInfo[r].rho_minus_half = rhoInfo[r].rho_i - 0.5 * D_RHO;
        } else {
            rhoInfo[r].inv_rho_i = 0.0;
            rhoInfo[r].inv_rho_i_sq = 0.0;
            rhoInfo[r].rho_plus_half = 0.5 * D_RHO;
            rhoInfo[r].rho_minus_half = 0.0;
        }
    }
    
    std::map<std::string, double> params = {
        {"R", R}, {"T", t_final}, {"dt", DT_3D}, {"N_steps", (double)n_steps},
        {"L", L_CYL}, {"H", H}, {"N_PHI", (double)N_PHI}, {"N_RHO", (double)N_RHO}, {"NZ", (double)NZ},
        {"D_PHI", D_PHI}, {"D_RHO", D_RHO}, {"DZ", DZ},
        {"D_U", D_U}, {"D_W", D_W}, {"CHI", CHI},
        {"ALPHA", ALPHA}, {"BETA", BETA}, {"GAMMA", GAMMA}, {"W_0", W_0},
        {"SAVE_EVERY_T", SAVE_EVERY_T_3D}
    };
    
    Writer writer("3D", params);
    
    const std::string timestamp = makeTimestamp();
    
    std::string spatio_filename = "results/3D_" + timestamp + "_spatiotemporal.dat";
    
    const double inv_h_rho_sq = 1.0 / (D_RHO * D_RHO);
    const double inv_h_phi_sq_1 = 1.0 / (D_PHI * D_PHI);
    const double inv_h_phi_sq_2 = 1.0 / ((2.0 * D_PHI) * (2.0 * D_PHI));
    const double inv_h_phi_sq_4 = 1.0 / ((4.0 * D_PHI) * (4.0 * D_PHI));
    const double inv_h_z_sq = 1.0 / (DZ * DZ);
    
    const int rhoQuarter = RHO_QUARTER;
    const int rhoHalf = RHO_HALF;
    
    std::cout << "Starting 3D simulation with N_steps = " << n_steps << "\n";
    std::cout << "dt = " << DT_3D << ", T = " << t_final << "\n";
    std::cout << "Grid: N_RHO = " << N_RHO << ", N_PHI = " << N_PHI << ", NZ = " << NZ << "\n";
    std::cout << "Saving: Every " << SAVE_EVERY_T_3D << " time units (" << save_interval << " steps)\n";
    std::cout << "Spatiotemporal: Saving " << SPATIOTEMPORAL_SAMPLES << " time samples\n\n";
    
    std::cout << "Saving initial snapshot at t = 0.0\n";
    writer.saveSnapshot3D(0.0, *u_curr_ptr);
    
    for (int j = 0; j <= n_steps; ++j) {
        double t = j * DT_3D;
        
        if (j % progress_interval == 0) {
            auto current_time = std::chrono::high_resolution_clock::now();
            std::chrono::duration<double> elapsed = current_time - start_time;
            double progress = 100.0 * j / n_steps;
            double steps_per_sec = (j > 0) ? j / elapsed.count() : 0.0;
            double eta_seconds = (j > 0) ? (n_steps - j) / steps_per_sec : 0.0;
            
            std::cout << "Progress: " << std::setw(5) << std::setprecision(1) << progress << "% "
                      << "(j=" << j << "/" << n_steps << ", t=" << t << "), "
                      << std::setprecision(1) << steps_per_sec << " steps/s, "
                      << "ETA: " << (eta_seconds/60.0) << " min\n";
        }
        
        if (j % spatiotemporal_interval == 0) {
            auto& u_curr = *u_curr_ptr;
            vector<double> avg_angular(N_PHI, 0.0);
            
            int rho_count = RHO_END_3D - RHO_START_3D + 1;
            int z_count = std::min(Z_END_3D, NZ - 1) - Z_START_3D + 1;
            
            for (int p = 0; p < N_PHI; ++p) {
                double sum = 0.0;
                for (int r = RHO_START_3D; r <= RHO_END_3D; ++r) {
                    for (int z = Z_START_3D; z <= std::min(Z_END_3D, NZ - 1); ++z) {
                        sum += u_curr[r][p][z];
                    }
                }
                avg_angular[p] = sum / (rho_count * z_count);
            }
            
            spatiotemporal_data.push_back(avg_angular);
        }
        
        auto& u_curr_values = *u_curr_ptr;
        auto& v_curr_values = *v_curr_ptr;
        auto& w_curr_values = *w_curr_ptr;
        auto& u_next_values = *u_next_ptr;
        auto& v_next_values = *v_next_ptr;
        auto& w_next_values = *w_next_ptr;
        
        #pragma omp parallel for schedule(dynamic, 2)
        for (int i_rho = N_RHO - 2; i_rho >= 1; --i_rho) {
            const double inv_rho_i = rhoInfo[i_rho].inv_rho_i;
            const double inv_rho_i_sq = rhoInfo[i_rho].inv_rho_i_sq;
            const double rho_plus_half = rhoInfo[i_rho].rho_plus_half;
            const double rho_minus_half = rhoInfo[i_rho].rho_minus_half;
            
            int phiInc = 1;
            double inv_h_phi_sq_local = inv_h_phi_sq_1;
            
            if (i_rho < rhoHalf) {
                phiInc = 2;
                inv_h_phi_sq_local = inv_h_phi_sq_2;
            }
            if (i_rho < rhoQuarter) {
                phiInc = 4;
                inv_h_phi_sq_local = inv_h_phi_sq_4;
            }
            
            for (int i_phi = 0; i_phi < N_PHI; i_phi += phiInc) {
                const int i_phi_plus = wrapPhi(i_phi + phiInc);
                const int i_phi_minus = wrapPhi(i_phi - phiInc);
                
                for (int i_z = 1; i_z < NZ - 1; ++i_z) {
                    const double u_curr = u_curr_values[i_rho][i_phi][i_z];
                    const double v_curr = v_curr_values[i_rho][i_phi][i_z];
                    const double w_curr = w_curr_values[i_rho][i_phi][i_z];
                    
                    const double u_rho_p = u_curr_values[i_rho + 1][i_phi][i_z];
                    const double u_rho_m = u_curr_values[i_rho - 1][i_phi][i_z];
                    const double u_phi_p = u_curr_values[i_rho][i_phi_plus][i_z];
                    const double u_phi_m = u_curr_values[i_rho][i_phi_minus][i_z];
                    const double u_z_p = u_curr_values[i_rho][i_phi][i_z + 1];
                    const double u_z_m = u_curr_values[i_rho][i_phi][i_z - 1];
                    
                    const double v_rho_p = v_curr_values[i_rho + 1][i_phi][i_z];
                    const double v_rho_m = v_curr_values[i_rho - 1][i_phi][i_z];
                    const double v_phi_p = v_curr_values[i_rho][i_phi_plus][i_z];
                    const double v_phi_m = v_curr_values[i_rho][i_phi_minus][i_z];
                    const double v_z_p = v_curr_values[i_rho][i_phi][i_z + 1];
                    const double v_z_m = v_curr_values[i_rho][i_phi][i_z - 1];
                    
                    const double w_rho_p = w_curr_values[i_rho + 1][i_phi][i_z];
                    const double w_rho_m = w_curr_values[i_rho - 1][i_phi][i_z];
                    const double w_phi_p = w_curr_values[i_rho][i_phi_plus][i_z];
                    const double w_phi_m = w_curr_values[i_rho][i_phi_minus][i_z];
                    const double w_z_p = w_curr_values[i_rho][i_phi][i_z + 1];
                    const double w_z_m = w_curr_values[i_rho][i_phi][i_z - 1];
                    
                    const double diff_u_rho = inv_rho_i * (
                        (rho_plus_half * (u_rho_p - u_curr) - 
                         rho_minus_half * (u_curr - u_rho_m)) * inv_h_rho_sq
                    );
                    const double diff_u_phi = inv_rho_i_sq * (
                        (u_phi_p - 2.0 * u_curr + u_phi_m) * inv_h_phi_sq_local
                    );
                    const double diff_u_z = (u_z_p - 2.0 * u_curr + u_z_m) * inv_h_z_sq;
                    const double diffusion_u = D_U * (diff_u_rho + diff_u_phi + diff_u_z);
                    
                    const double u_rho_half_p = 0.5 * (u_rho_p + u_curr);
                    const double u_rho_half_m = 0.5 * (u_curr + u_rho_m);
                    const double chem_u_rho = inv_rho_i * (
                        (rho_plus_half * u_rho_half_p * (v_rho_p - v_curr) - 
                         rho_minus_half * u_rho_half_m * (v_curr - v_rho_m)) * inv_h_rho_sq
                    );
                    const double U_phi_half_p = 0.5 * (u_phi_p + u_curr);
                    const double U_phi_half_m = 0.5 * (u_curr + u_phi_m);
                    const double chem_u_phi = inv_rho_i_sq * (
                        (U_phi_half_p * (v_phi_p - v_curr) - 
                         U_phi_half_m * (v_curr - v_phi_m)) * inv_h_phi_sq_local
                    );
                    const double U_z_half_p = 0.5 * (u_z_p + u_curr);
                    const double U_z_half_m = 0.5 * (u_curr + u_z_m);
                    const double chem_U_z = (
                        (U_z_half_p * (v_z_p - v_curr) - 
                         U_z_half_m * (v_curr - v_z_m)) * inv_h_z_sq
                    );
                    const double chemotaxis_u = -CHI * (chem_u_rho + chem_u_phi + chem_U_z);
                    const double reaction_u = ALPHA * u_curr * (1.0 - u_curr / w_curr);
                    const double dU_dt = diffusion_u + chemotaxis_u + reaction_u;
                    u_next_values[i_rho][i_phi][i_z] = u_curr + DT_3D * dU_dt;
                    
                    const double diff_v_rho = inv_rho_i * (
                        (rho_plus_half * (v_rho_p - v_curr) - 
                         rho_minus_half * (v_curr - v_rho_m)) * inv_h_rho_sq
                    );
                    const double diff_v_phi = inv_rho_i_sq * (
                        (v_phi_p - 2.0 * v_curr + v_phi_m) * inv_h_phi_sq_local
                    );
                    const double diff_v_z = (v_z_p - 2.0 * v_curr + v_z_m) * inv_h_z_sq;
                    const double diffusion_v = diff_v_rho + diff_v_phi + diff_v_z;
                    const double production_v = u_curr / (1.0 + BETA * u_curr);
                    const double decay_v = v_curr;
                    const double dV_dt = diffusion_v + production_v - decay_v;
                    v_next_values[i_rho][i_phi][i_z] = v_curr + DT_3D * dV_dt;
                    
                    const double diff_w_rho = inv_rho_i * (
                        (rho_plus_half * (w_rho_p - w_curr) - 
                         rho_minus_half * (w_curr - w_rho_m)) * inv_h_rho_sq
                    );
                    const double diff_w_phi = inv_rho_i_sq * (
                        (w_phi_p - 2.0 * w_curr + w_phi_m) * inv_h_phi_sq_local
                    );
                    const double diff_w_z = (w_z_p - 2.0 * w_curr + w_z_m) * inv_h_z_sq;
                    const double diffusion_w = D_W * (diff_w_rho + diff_w_phi + diff_w_z);
                    const double consumption_w = GAMMA * u_curr;
                    const double dw_dt = diffusion_w - consumption_w;
                    w_next_values[i_rho][i_phi][i_z] = w_curr + DT_3D * dw_dt;
                }
            }
        }
        
        std::swap(u_curr_ptr, u_next_ptr);
        std::swap(v_curr_ptr, v_next_ptr);
        std::swap(w_curr_ptr, w_next_ptr);
        
        auto& u_after_swap = *u_curr_ptr;
        auto& v_after_swap = *v_curr_ptr;
        auto& w_after_swap = *w_curr_ptr;
        
        #pragma omp parallel for collapse(2)
        for (int i_rho = 1; i_rho < rhoQuarter; ++i_rho) {
            for (int i_z = 1; i_z < NZ; ++i_z) {
                for (int i_phi = 0; i_phi < N_PHI; ++i_phi) {
                    if (i_phi % 4 == 0) continue;
                    const int phi_L = (i_phi / 4) * 4;
                    const int phi_R = (phi_L + 4) % N_PHI;
                    const double weight = double(i_phi - phi_L) / 4.0;
                    u_after_swap[i_rho][i_phi][i_z] = (1.0 - weight) * u_after_swap[i_rho][phi_L][i_z] + 
                                                       weight * u_after_swap[i_rho][phi_R][i_z];
                    v_after_swap[i_rho][i_phi][i_z] = (1.0 - weight) * v_after_swap[i_rho][phi_L][i_z] + 
                                                       weight * v_after_swap[i_rho][phi_R][i_z];
                    w_after_swap[i_rho][i_phi][i_z] = (1.0 - weight) * w_after_swap[i_rho][phi_L][i_z] + 
                                                       weight * w_after_swap[i_rho][phi_R][i_z];
                }
            }
        }
        
        #pragma omp parallel for collapse(2)
        for (int i_rho = rhoQuarter; i_rho < rhoHalf; ++i_rho) {
            for (int i_z = 1; i_z < NZ; ++i_z) {
                for (int i_phi = 0; i_phi < N_PHI; ++i_phi) {
                    if (i_phi % 2 == 0) continue;
                    const int phi_L = (i_phi / 2) * 2;
                    const int phi_R = (phi_L + 2) % N_PHI;
                    const double weight = double(i_phi - phi_L) / 2.0;
                    u_after_swap[i_rho][i_phi][i_z] = (1.0 - weight) * u_after_swap[i_rho][phi_L][i_z] + 
                                                       weight * u_after_swap[i_rho][phi_R][i_z];
                    v_after_swap[i_rho][i_phi][i_z] = (1.0 - weight) * v_after_swap[i_rho][phi_L][i_z] + 
                                                       weight * v_after_swap[i_rho][phi_R][i_z];
                    w_after_swap[i_rho][i_phi][i_z] = (1.0 - weight) * w_after_swap[i_rho][phi_L][i_z] + 
                                                       weight * w_after_swap[i_rho][phi_R][i_z];
                }
            }
        }
        
        const int transition_rhos[] = {rhoQuarter - 1, rhoQuarter, rhoQuarter + 1,
                                        rhoHalf - 1, rhoHalf, rhoHalf + 1};
        for (int transition_rho : transition_rhos) {
            if (transition_rho < 1 || transition_rho >= N_RHO - 1) continue;
            #pragma omp parallel for collapse(2)
            for (int i_z = 1; i_z < NZ; ++i_z) {
                for (int i_phi = 0; i_phi < N_PHI; ++i_phi) {
                    const double u_smoothed = 0.5 * u_after_swap[transition_rho][i_phi][i_z] + 
                                             0.25 * u_after_swap[transition_rho-1][i_phi][i_z] +
                                             0.25 * u_after_swap[transition_rho+1][i_phi][i_z];
                    const double v_smoothed = 0.5 * v_after_swap[transition_rho][i_phi][i_z] + 
                                             0.25 * v_after_swap[transition_rho-1][i_phi][i_z] +
                                             0.25 * v_after_swap[transition_rho+1][i_phi][i_z];
                    const double o_smoothed = 0.5 * w_after_swap[transition_rho][i_phi][i_z] + 
                                             0.25 * w_after_swap[transition_rho-1][i_phi][i_z] +
                                             0.25 * w_after_swap[transition_rho+1][i_phi][i_z];
                    u_after_swap[transition_rho][i_phi][i_z] = u_smoothed;
                    v_after_swap[transition_rho][i_phi][i_z] = v_smoothed;
                    w_after_swap[transition_rho][i_phi][i_z] = o_smoothed;
                }
            }
        }
        
        #pragma omp parallel for collapse(2)
        for (int i_rho = 0; i_rho < N_RHO; ++i_rho) {
            for (int i_phi = 0; i_phi < N_PHI; ++i_phi) {
                u_after_swap[i_rho][i_phi][0] = u_after_swap[i_rho][i_phi][1];
                v_after_swap[i_rho][i_phi][0] = v_after_swap[i_rho][i_phi][1];
                w_after_swap[i_rho][i_phi][0] = w_after_swap[i_rho][i_phi][1];
            }
        }
        
        #pragma omp parallel for collapse(2)
        for (int i_rho = 0; i_rho < N_RHO; ++i_rho) {
            for (int i_phi = 0; i_phi < N_PHI; ++i_phi) {
                u_after_swap[i_rho][i_phi][NZ - 1] = u_after_swap[i_rho][i_phi][NZ - 2];
                v_after_swap[i_rho][i_phi][NZ - 1] = v_after_swap[i_rho][i_phi][NZ - 2];
                w_after_swap[i_rho][i_phi][NZ - 1] = W_0;
            }
        }
        
        #pragma omp parallel for collapse(2)
        for (int i_phi = 0; i_phi < N_PHI; ++i_phi) {
            for (int i_z = 0; i_z < NZ; ++i_z) {
                u_after_swap[N_RHO - 1][i_phi][i_z] = u_after_swap[N_RHO - 2][i_phi][i_z];
                v_after_swap[N_RHO - 1][i_phi][i_z] = v_after_swap[N_RHO - 2][i_phi][i_z];
                w_after_swap[N_RHO - 1][i_phi][i_z] = w_after_swap[N_RHO - 2][i_phi][i_z];
            }
        }
        
        #pragma omp parallel for collapse(2)
        for (int i_phi = 0; i_phi < N_PHI; ++i_phi) {
            for (int i_z = 0; i_z < NZ; ++i_z) {
                u_after_swap[0][i_phi][i_z] = u_after_swap[1][i_phi][i_z];
                v_after_swap[0][i_phi][i_z] = v_after_swap[1][i_phi][i_z];
                w_after_swap[0][i_phi][i_z] = w_after_swap[1][i_phi][i_z];
            }
        }
        
        if (j % save_interval == 0) {
            std::cout << "Saving snapshot at t = " << t << "\n";

            if (checkForNaN(u_after_swap, v_after_swap, w_after_swap, j, t)) {
                std::cerr << "Aborting simulation due to NaN.\n";
                return 1;
            }
            
            writer.saveSnapshot3D(t, u_after_swap);
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end_time - start_time;
    
    std::cout << "\n===== SIMULATION COMPLETE =====\n";
    std::cout << "Total time: " << elapsed.count() << " seconds (" 
              << (elapsed.count()/60.0) << " minutes)\n";
    std::cout << "Average: " << (n_steps / elapsed.count()) << " steps/second\n\n";
    
    saveSpatiotemporalData(spatio_filename, spatiotemporal_data, t_final, std::to_string(L_CYL), "3D model");
    
    auto& u_final = *u_curr_ptr;
    auto& v_final = *v_curr_ptr;
    auto& w_final = *w_curr_ptr;
    
    double u_min = std::numeric_limits<double>::infinity();
    double u_max = -std::numeric_limits<double>::infinity();
    double v_min = std::numeric_limits<double>::infinity();
    double v_max = -std::numeric_limits<double>::infinity();
    double o_min = std::numeric_limits<double>::infinity();
    double o_max = -std::numeric_limits<double>::infinity();
    bool has_nan = false;
    
    #pragma omp parallel for reduction(min:u_min,v_min,o_min) reduction(max:u_max,v_max,o_max) collapse(2)
    for (int r = 0; r < N_RHO; ++r) {
        for (int p = 0; p < N_PHI; ++p) {
            for (int z = 0; z < NZ; ++z) {
                if (std::isnan(u_final[r][p][z]) || std::isnan(v_final[r][p][z]) || std::isnan(w_final[r][p][z])) {
                    has_nan = true;
                }
                u_min = min(u_min, u_final[r][p][z]);
                u_max = max(u_max, u_final[r][p][z]);
                v_min = min(v_min, v_final[r][p][z]);
                v_max = max(v_max, v_final[r][p][z]);
                o_min = min(o_min, w_final[r][p][z]);
                o_max = max(o_max, w_final[r][p][z]);
            }
        }
    }
    
    std::cout << "===== FINAL STATISTICS =====\n";
    std::cout << "U: min = " << u_min << ", max = " << u_max << "\n";
    std::cout << "V: min = " << v_min << ", max = " << v_max << "\n";
    std::cout << "O: min = " << o_min << ", max = " << o_max << "\n";
    
    if (has_nan) {
        std::cout << "WARNING: NaN detected in solution!\n";
    } else {
        std::cout << "No NaN detected.\n";
    }
    
    return 0;
}