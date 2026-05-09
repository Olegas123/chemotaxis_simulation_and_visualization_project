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
#include <ctime>

#ifdef _OPENMP
#include <omp.h>
#endif

using std::vector;
using std::max, std::min;

void initializeRandomU(vector<vector<double>>& u) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::normal_distribution<double> dist(1.0, 0.1);
    
    for (int i = 0; i < N_PHI; ++i) {
        for (int j = 0; j <= NZ; ++j) {
            u[i][j] = dist(gen);
        }
    }
}

int main(int argc, char* argv[]) {
    std::cout << std::fixed << std::setprecision(6);
    SIM_INIT(argc, argv, DT_2D_CYL, SAVE_EVERY_T_2D_CYL);
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    vector<vector<double>> u_current(N_PHI, vector<double>(NZ, 0.0));
    vector<vector<double>> v_current(N_PHI, vector<double>(NZ, 0.0));
    vector<vector<double>> w_current(N_PHI, vector<double>(NZ, 1.0));
    vector<vector<double>> u_next(N_PHI, vector<double>(NZ, 0.0));
    vector<vector<double>> v_next(N_PHI, vector<double>(NZ, 0.0));
    vector<vector<double>> w_next(N_PHI, vector<double>(NZ, 1.0));

    #ifdef _OPENMP
    omp_set_num_threads(OPEN_MP_THREAD_COUNT);
    #else
    std::cout << "WARNING: OpenMP not enabled! Recompile with -fopenmp\n";
    #endif
    
    auto* u_curr_ptr = &u_current;
    auto* v_curr_ptr = &v_current;
    auto* w_curr_ptr = &w_current;
    auto* u_next_ptr = &u_next;
    auto* v_next_ptr = &v_next;
    auto* w_next_ptr = &w_next;
    
    vector<vector<double>> spatiotemporal_data;
    spatiotemporal_data.reserve(SPATIOTEMPORAL_SAMPLES);
    int spatiotemporal_interval = std::max(1, n_steps / SPATIOTEMPORAL_SAMPLES);
    
    if (!ic_file.empty()) {
        std::cout << "Loading initial conditions from: " << ic_file << "\n";
        if (!load2DCylindricalInitialConditions(ic_file, *u_curr_ptr, N_PHI, NZ)) {
            std::cerr << "Failed to load IC, using random instead\n";
            initializeRandomU(*u_curr_ptr);
        }
    } else {
        std::cout << "No IC file provided, using random initialization\n";
        initializeRandomU(*u_curr_ptr);
    }

    std::cout << "Init zero: " << u_current[0][NZ-1] << std::endl;
    
    std::map<std::string, double> params = {
        {"R", R}, {"T", t_final}, {"dt", DT_2D_CYL}, {"N_steps", (double)n_steps},
        {"L", L_CYL}, {"H", H}, {"N_PHI", (double)N_PHI}, {"NZ", (double)NZ},
        {"DX_CYL", DX_CYL}, {"DZ", DZ},
        {"D_U", D_U}, {"D_W", D_W}, {"CHI", CHI},
        {"ALPHA", ALPHA}, {"BETA", BETA}, {"GAMMA", GAMMA}, {"W_0", W_0},
        {"SAVE_EVERY_T", SAVE_EVERY_T_2D_CYL}
    };
    
    Writer writer("2D_side", params);
    
    const std::string timestamp = makeTimestamp();
    
    std::string spatio_filename = "results/2D_side_" + timestamp + "_spatiotemporal.dat";
    
    const double inv_dx_sq = 1.0 / (DX_CYL * DX_CYL);
    const double inv_dz_sq = 1.0 / (DZ * DZ);
    
    std::cout << "Starting 2D side simulation\n";
    std::cout << "Grid: N_PHI = " << N_PHI << ", NZ = " << NZ << "\n";
    std::cout << "Time steps: N_steps = " << n_steps << ", dt = " << DT_2D_CYL << ", T = " << t_final << "\n";
    std::cout << "Saving: Every " << SAVE_EVERY_T_2D_CYL << " time units (" << save_interval << " steps)\n";
    std::cout << "Spatiotemporal: Saving " << SPATIOTEMPORAL_SAMPLES << " time samples\n\n";
    
    std::cout << "Saving initial snapshot at t = 0.0\n";
    writer.saveSnapshot2Dside(0.0, *u_curr_ptr);

    double last_save_time = 0.0;
    
    for (int t = 0; t <= n_steps; ++t) {
        double current_time = t * DT_2D_CYL;
        
        auto& u_curr_values = *u_curr_ptr;
        auto& v_curr_values = *v_curr_ptr;
        auto& w_curr_values = *w_curr_ptr;
        auto& u_next_values = *u_next_ptr;
        auto& v_next_values = *v_next_ptr;
        auto& w_next_values = *w_next_ptr;
        
        if (t % progress_interval == 0) {
            auto now_time = std::chrono::high_resolution_clock::now();
            std::chrono::duration<double> elapsed = now_time - start_time;
            double progress = 100.0 * t / n_steps;
            double steps_per_sec = (t > 0) ? t / elapsed.count() : 0.0;
            double eta_seconds = (t > 0) ? (n_steps - t) / steps_per_sec : 0.0;
            
            std::cout << "Progress: " << std::setw(5) << std::setprecision(1) << progress << "% "
                      << "(t=" << t << "/" << n_steps << ", time=" << current_time << "), "
                      << std::setprecision(1) << steps_per_sec << " steps/s, "
                      << "ETA: " << (eta_seconds/60.0) << " min\n";
        }
        
        if (t % spatiotemporal_interval == 0) {
            vector<double> avg_line(N_PHI, 0.0);
            
            int z_count = std::min(Z_END_2D, NZ - 1) - Z_START_2D + 1;
            for (int i = 0; i < N_PHI; ++i) {
                double sum = 0.0;
                for (int z = Z_START_2D; z <= std::min(Z_END_2D, NZ - 1); ++z) {
                    sum += u_curr_values[i][z];
                }
                avg_line[i] = sum / z_count;
            }
            
            spatiotemporal_data.push_back(avg_line);
        }
        
        #pragma omp parallel for collapse(2) schedule(static)
        for (int i = 0; i < N_PHI; ++i) {
            for (int j = 1; j < NZ - 1; ++j) {
                const int i_plus = wrapPhi(i + 1);
                const int i_minus = wrapPhi(i - 1);
                
                const double u_curr = u_curr_values[i][j];
                const double v_curr = v_curr_values[i][j];
                const double w_curr = w_curr_values[i][j];
                
                const double u_xp = u_curr_values[i_plus][j];
                const double u_xm = u_curr_values[i_minus][j];
                const double u_zp = u_curr_values[i][j + 1];
                const double u_zm = u_curr_values[i][j - 1];
                
                const double v_xp = v_curr_values[i_plus][j];
                const double v_xm = v_curr_values[i_minus][j];
                const double v_zp = v_curr_values[i][j + 1];
                const double v_zm = v_curr_values[i][j - 1];
                
                const double w_xp = w_curr_values[i_plus][j];
                const double w_xm = w_curr_values[i_minus][j];
                const double w_zp = w_curr_values[i][j + 1];
                const double w_zm = w_curr_values[i][j - 1];
                
                const double diff_U = D_U * (
                    (u_xp + u_xm - 2.0 * u_curr) * inv_dx_sq +
                    (u_zp + u_zm - 2.0 * u_curr) * inv_dz_sq
                );
                
                const double chem_x = (
                    (u_xp + u_curr) * 0.5 * (v_xp - v_curr) -
                    (u_curr + u_xm) * 0.5 * (v_curr - v_xm)
                ) * inv_dx_sq;
                
                const double chem_z = (
                    (u_zp + u_curr) * 0.5 * (v_zp - v_curr) -
                    (u_curr + u_zm) * 0.5 * (v_curr - v_zm)
                ) * inv_dz_sq;
                
                const double chemotaxis_U = CHI * (chem_x + chem_z);
                const double reaction_U = ALPHA * u_curr * (1.0 - u_curr / w_curr);
                
                u_next_values[i][j] = u_curr + DT_2D_CYL * (diff_U - chemotaxis_U + reaction_U);
                
                const double diff_V = (
                    (v_xp + v_xm - 2.0 * v_curr) * inv_dx_sq +
                    (v_zp + v_zm - 2.0 * v_curr) * inv_dz_sq
                );
                
                const double production_V = u_curr / (1.0 + BETA * u_curr);
                const double decay_V = v_curr;
                
                v_next_values[i][j] = v_curr + DT_2D_CYL * (diff_V + production_V - decay_V);
                
                const double diff_W = D_W * (
                    (w_xp + w_xm - 2.0 * w_curr) * inv_dx_sq +
                    (w_zp + w_zm - 2.0 * w_curr) * inv_dz_sq
                );
                
                const double consumption_W = GAMMA * u_curr;
                
                w_next_values[i][j] = w_curr + DT_2D_CYL * (diff_W - consumption_W);
            }
        }
        
        std::swap(u_curr_ptr, u_next_ptr);
        std::swap(v_curr_ptr, v_next_ptr);
        std::swap(w_curr_ptr, w_next_ptr);
        
        auto& u_after_swap = *u_curr_ptr;
        auto& v_after_swap = *v_curr_ptr;
        auto& w_after_swap = *w_curr_ptr;
        
        #pragma omp parallel for
        for (int i = 0; i < N_PHI; ++i) {
            u_after_swap[i][0] = u_after_swap[i][1];
            v_after_swap[i][0] = v_after_swap[i][1];
            w_after_swap[i][0] = w_after_swap[i][1];
            
            u_after_swap[i][NZ - 1] = u_after_swap[i][NZ-2];
            v_after_swap[i][NZ - 1] = v_after_swap[i][NZ-2];
            w_after_swap[i][NZ - 1] = W_0;
        }
        
        if (current_time - last_save_time >= SAVE_EVERY_T_2D_CYL - 1e-10) {
            std::cout << "Saving snapshot at t = " << current_time << "\n";
            writer.saveSnapshot2Dside(current_time, u_after_swap);
            last_save_time = current_time;
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end_time - start_time;
    
    std::cout << "\n===== SIMULATION COMPLETE =====\n";
    std::cout << "Total time: " << elapsed.count() << " seconds\n";
    
    saveSpatiotemporalData(spatio_filename, spatiotemporal_data, t_final, std::to_string(L_CYL), "2D side (cylindrical) model");
    
    auto& u_final = *u_curr_ptr;
    double u_min = std::numeric_limits<double>::infinity();
    double u_max = -std::numeric_limits<double>::infinity();
    bool has_nan = false;
    
    for (int i = 0; i < N_PHI; ++i) {
        for (int j = 0; j < NZ; ++j) {
            if (std::isnan(u_final[i][j])) {
                has_nan = true;
                return 1;
            }
            u_min = min(u_min, u_final[i][j]);
            u_max = max(u_max, u_final[i][j]);
        }
    }
    
    std::cout << "Final u: min = " << u_min << ", max = " << u_max << "\n";
    if (has_nan) {
        std::cout << "WARNING: NaN detected in solution!\n";
    } else {
        std::cout << "No NaN detected.\n";
    }
    
    return 0;
}