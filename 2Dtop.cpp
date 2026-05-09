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
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    
    for (auto& row : u) {
        for (auto& val : row) {
            val = dist(gen);
        }
    }
}

int main(int argc, char* argv[]) {
    std::cout << std::fixed << std::setprecision(6);
    SIM_INIT(argc, argv, DT_2D_POLAR, SAVE_EVERY_T_2D_POLAR);

    #ifdef _OPENMP
    omp_set_num_threads(OPEN_MP_THREAD_COUNT);
    #else
    std::cout << "WARNING: OpenMP not enabled! Recompile with -fopenmp\n";
    #endif
    
    vector<vector<double>> u_current(N_RHO, vector<double>(N_PHI, 0.0));
    vector<vector<double>> v_current(N_RHO, vector<double>(N_PHI, 0.0));
    auto u_next = u_current;
    auto v_next = v_current;

    auto* u_curr_ptr = &u_current;
    auto* u_next_ptr = &u_next;
    auto* v_curr_ptr = &v_current;
    auto* v_next_ptr = &v_next;
    
    vector<vector<double>> spatiotemporal_data;
    spatiotemporal_data.reserve(SPATIOTEMPORAL_SAMPLES);
    int spatiotemporal_interval = std::max(1, n_steps / SPATIOTEMPORAL_SAMPLES);
    
    if (!ic_file.empty()) {
        std::cout << "Loading initial conditions from: " << ic_file << "\n";
        if (!load2DPolarInitialConditions(ic_file, *u_curr_ptr, N_RHO, N_PHI)) {
            std::cerr << "Failed to load IC, using random instead\n";
            initializeRandomU(*u_curr_ptr);
        }
    } else {
        std::cout << "No IC file provided, using random initialization\n";
        initializeRandomU(*u_curr_ptr);
    }

    std::cout << "Init zero: " << (*u_curr_ptr)[N_RHO-1][0] << std::endl;
    
    const double L = 2.0 * M_PI * R;
    
    std::map<std::string, double> params = {
        {"R", R}, {"T", t_final}, {"dt", DT_2D_POLAR}, {"N_steps", (double)n_steps},
        {"L", L}, {"H", R}, {"N_PHI", (double)N_PHI}, {"N_RHO", (double)N_RHO},
        {"D_PHI", D_PHI}, {"D_RHO", D_RHO},
        {"D_U", D_U}, {"CHI", CHI},
        {"ALPHA", ALPHA}, {"BETA", BETA}, {"GAMMA", 0.0}, {"W_0", W_0},
        {"SAVE_EVERY_T", SAVE_EVERY_T_2D_POLAR}
    };
    
    Writer writer("2D_top", params);
    
    const std::string timestamp = makeTimestamp();
    
    std::string spatio_filename = "results/2D_top_" + timestamp + "_spatiotemporal.dat";
    
    // Some precomputed constants
    const double delta_rho_sq = D_RHO * D_RHO;
    const double inv_delta_rho_sq = 1.0 / delta_rho_sq;
    
    const double delta_phi_sq_1 = D_PHI * D_PHI;
    const double inv_delta_phi_sq_1 = 1.0 / delta_phi_sq_1;
    
    const double delta_phi_sq_2 = (2.0 * D_PHI) * (2.0 * D_PHI);
    const double inv_delta_phi_sq_2 = 1.0 / delta_phi_sq_2;
    
    const double delta_phi_sq_4 = (4.0 * D_PHI) * (4.0 * D_PHI);
    const double inv_delta_phi_sq_4 = 1.0 / delta_phi_sq_4;
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    std::cout << "Starting simulation with N_steps = " << n_steps << "\n";
    std::cout << "dt = " << DT_2D_POLAR << ", T = " << t_final << "\n";
    std::cout << "Grid: N_RHO = " << N_RHO << ", N_PHI = " << N_PHI << "\n";
    std::cout << "Saving: Every " << SAVE_EVERY_T_2D_POLAR << " time units (" << save_interval << " steps)\n";
    std::cout << "Spatiotemporal: Saving " << SPATIOTEMPORAL_SAMPLES << " time samples\n\n";
    
    std::cout << "Saving initial snapshot at t = 0.0\n";
    writer.saveSnapshot2Dtop(0.0, *u_curr_ptr);

    double last_save_time = 0.0;
    
    for (int step = 0; step <= n_steps; ++step) {
        double t = step * DT_2D_POLAR;

        auto& u_curr = *u_curr_ptr;
        auto& v_curr = *v_curr_ptr;
        auto& u_nxt  = *u_next_ptr;
        auto& v_nxt  = *v_next_ptr;
        
        if (step % progress_interval == 0) {
            double max_u = 0.0;
            for (const auto& row : u_curr) {
                max_u = std::max(max_u, *std::max_element(row.begin(), row.end()));
            }
            std::cout << "step = " << step << " (t = " << t << "), max(u) = " << max_u << "\n";
        }
        
        if (step % spatiotemporal_interval == 0) {
            vector<double> avg_angular(N_PHI, 0.0);
            
            int rho_count = RHO_END - RHO_START + 1;
            for (int p = 0; p < N_PHI; ++p) {
                double sum = 0.0;
                for (int r = RHO_START; r <= RHO_END; ++r) {
                    sum += u_curr[r][p];
                }
                avg_angular[p] = sum / rho_count;
            }
            
            spatiotemporal_data.push_back(avg_angular);
        }
        
        #pragma omp parallel for schedule(dynamic, 2)
        for (int rho = N_RHO - 2; rho >= 1; --rho) {
            double rho_i = rho * D_RHO;
            double inv_rho_i = 1.0 / rho_i;
            double inv_rho_i_sq = inv_rho_i * inv_rho_i;
            double rho_plus_half = rho_i + 0.5 * D_RHO;
            double rho_minus_half = rho_i - 0.5 * D_RHO;
            
            int phiInc = 1;
            double inv_dphi_sq_local = inv_delta_phi_sq_1;
            
            if (rho < RHO_HALF) {
                phiInc = 2;
                inv_dphi_sq_local = inv_delta_phi_sq_2;
            }
            if (rho < RHO_QUARTER) {
                phiInc = 4;
                inv_dphi_sq_local = inv_delta_phi_sq_4;
            }
            
            for (int phi = 0; phi < N_PHI; phi += phiInc) {
                int phi_plus = wrapPhi(phi + phiInc);
                int phi_minus = wrapPhi(phi - phiInc);
                
                double u_rho_phi = u_curr[rho][phi];
                double u_rho_plus_1_phi = u_curr[rho + 1][phi];
                double u_rho_minus_1_phi = u_curr[rho - 1][phi];
                double u_rho_phi_plus = u_curr[rho][phi_plus];
                double u_rho_phi_minus = u_curr[rho][phi_minus];
                
                double v_rho_phi = v_curr[rho][phi];
                double v_rho_plus_1_phi = v_curr[rho + 1][phi];
                double v_rho_minus_1_phi = v_curr[rho - 1][phi];
                double v_rho_phi_plus = v_curr[rho][phi_plus];
                double v_rho_phi_minus = v_curr[rho][phi_minus];
                
                // u equation
                double diff_u_radial = inv_rho_i * (
                    (rho_plus_half * (u_rho_plus_1_phi - u_rho_phi) -
                     rho_minus_half * (u_rho_phi - u_rho_minus_1_phi)) * inv_delta_rho_sq
                );
                
                double diff_u_angular = inv_rho_i_sq * (
                    (u_rho_phi_plus - 2.0 * u_rho_phi + u_rho_phi_minus) * inv_dphi_sq_local
                );
                
                double u_face_plus = 0.5 * (u_rho_plus_1_phi + u_rho_phi);
                double u_face_minus = 0.5 * (u_rho_minus_1_phi + u_rho_phi);
                
                double chem_u_radial = inv_rho_i * (
                    (rho_plus_half * u_face_plus * (v_rho_plus_1_phi - v_rho_phi) -
                     rho_minus_half * u_face_minus * (v_rho_phi - v_rho_minus_1_phi)) * inv_delta_rho_sq
                );
                
                double u_face_phi_plus = 0.5 * (u_rho_phi_plus + u_rho_phi);
                double u_face_phi_minus = 0.5 * (u_rho_phi + u_rho_phi_minus);
                
                double chem_u_angular = inv_rho_i_sq * (
                    (u_face_phi_plus * (v_rho_phi_plus - v_rho_phi) -
                     u_face_phi_minus * (v_rho_phi - v_rho_phi_minus)) * inv_dphi_sq_local
                );
                
                double reaction_u = ALPHA * u_rho_phi * (1.0 - u_rho_phi);
                
                double dudt = D_U * (diff_u_radial + diff_u_angular) -
                             CHI * (chem_u_radial + chem_u_angular) +
                             reaction_u;
                
                u_nxt[rho][phi] = u_rho_phi + DT_2D_POLAR * dudt;
                
                double diff_v_radial = inv_rho_i * (
                    (rho_plus_half * (v_rho_plus_1_phi - v_rho_phi) -
                     rho_minus_half * (v_rho_phi - v_rho_minus_1_phi)) * inv_delta_rho_sq
                );
                
                double diff_v_angular = inv_rho_i_sq * (
                    (v_rho_phi_plus - 2.0 * v_rho_phi + v_rho_phi_minus) * inv_dphi_sq_local
                );
                
                double prod_v = (u_rho_phi / (1.0 + BETA * u_rho_phi)) - v_rho_phi;
                
                double dvdt = (diff_v_radial + diff_v_angular) + prod_v;
                
                v_nxt[rho][phi] = v_rho_phi + DT_2D_POLAR * dvdt;
            }
        }
        
        fillMissingPhiValues(u_nxt);
        fillMissingPhiValues(v_nxt);
        
        #pragma omp parallel for schedule(static)
        for (int phi = 0; phi < N_PHI / 2; ++phi) {
            int phi_opp = phi + N_PHI / 2;
            double u_avg = 0.5 * (u_nxt[1][phi] + u_nxt[1][phi_opp]);
            double v_avg = 0.5 * (v_nxt[1][phi] + v_nxt[1][phi_opp]);
            u_nxt[0][phi] = u_avg;
            u_nxt[0][phi_opp] = u_avg;
            v_nxt[0][phi] = v_avg;
            v_nxt[0][phi_opp] = v_avg;
        }
        
        #pragma omp parallel for schedule(static)
        for (int phi = 0; phi < N_PHI; ++phi) {
            u_nxt[N_RHO - 1][phi] = u_nxt[N_RHO - 2][phi];
            v_nxt[N_RHO - 1][phi] = v_nxt[N_RHO - 2][phi];
        }
        
        std::swap(u_curr_ptr, u_next_ptr);
        std::swap(v_curr_ptr, v_next_ptr);
        
        if (t - last_save_time >= SAVE_EVERY_T_2D_POLAR - 1e-10) {
            std::cout << "Saving snapshot at t = " << t << "\n";
            writer.saveSnapshot2Dtop(t, *u_curr_ptr);
            last_save_time = t;
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end_time - start_time;
    
    std::cout << "\n===== SIMULATION COMPLETE =====\n";
    std::cout << "Total time: " << elapsed.count() << " seconds\n";
    
    saveSpatiotemporalData(spatio_filename, spatiotemporal_data, t_final, std::to_string(L_CYL), "2D polar model");
    
    return 0;
}