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
using std::max;
using std::min;


void initializeRandomFields(vector<vector<double>>& u_top_current, vector<vector<double>>& u_side_current) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<double> dist(0.5, 1.5);
    
    for (auto& row : u_top_current) {
        for (auto& val : row) {
            val = dist(gen);
        }
    }
    
    for (auto& row : u_side_current) {
        for (auto& val : row) {
            val = dist(gen);
        }
    }
}

int main(int argc, char* argv[]) {
    std::cout << std::fixed << std::setprecision(6);
    SIM_INIT(argc, argv, DT_2D_COMBINED, SAVE_EVERY_T_2D_COMBINED);

    #ifdef _OPENMP
    omp_set_num_threads(OPEN_MP_THREAD_COUNT);
    #else
    std::cout << "WARNING: OpenMP not enabled! Recompile with -fopenmp\n";
    #endif
        
    vector<vector<double>> u_top_current(N_RHO, vector<double>(N_PHI, 0.0));
    vector<vector<double>> v_top_current(N_RHO, vector<double>(N_PHI, 0.0));
    auto u_top_next = u_top_current;
    auto v_top_next = v_top_current;
    
    vector<vector<double>> u_side_current(N_PHI, vector<double>(NZ, 0.0));
    vector<vector<double>> v_side_current(N_PHI, vector<double>(NZ, 0.0));
    vector<vector<double>> w_side_current(N_PHI, vector<double>(NZ, 1.0));
    
    vector<vector<double>> u_side_next(N_PHI, vector<double>(NZ, 0.0));
    vector<vector<double>> v_side_next(N_PHI, vector<double>(NZ, 0.0));
    vector<vector<double>> w_side_next(N_PHI, vector<double>(NZ, 0.0));

    auto* u_top_curr_ptr = &u_top_current;
    auto* u_top_next_ptr = &u_top_next;
    auto* v_top_curr_ptr = &v_top_current;
    auto* v_top_next_ptr = &v_top_next;
    auto* u_side_curr_ptr = &u_side_current;
    auto* u_side_next_ptr = &u_side_next;
    auto* v_side_curr_ptr = &v_side_current;
    auto* v_side_next_ptr = &v_side_next;
    auto* w_side_curr_ptr = &w_side_current;
    auto* w_side_next_ptr = &w_side_next;
    
    vector<vector<double>> spatiotemporal_data;
    spatiotemporal_data.reserve(SPATIOTEMPORAL_SAMPLES);
    int spatiotemporal_interval = std::max(1, n_steps / SPATIOTEMPORAL_SAMPLES);
        
    if (!ic_file.empty() && !ic_file2.empty()) {
        std::cout << "Loading initial conditions:\n";
        std::cout << "  Top (polar): " << ic_file << "\n";
        std::cout << "  Side (cyl):  " << ic_file2 << "\n";
        
        bool top_ok = load2DPolarInitialConditions(ic_file, *u_top_curr_ptr, N_RHO, N_PHI);
        bool side_ok = load2DCylindricalInitialConditions(ic_file2, *u_side_curr_ptr, N_PHI, NZ);
        
        if (!top_ok || !side_ok) {
            std::cerr << "Failed to load one or both IC files, using random instead\n";
            initializeRandomFields(*u_top_curr_ptr, *u_side_curr_ptr);
        }
    } else {
        std::cout << "No IC files provided, using random initialization\n";
        initializeRandomFields(*u_top_curr_ptr, *u_side_curr_ptr);
    }
    
    std::cout << "Top Init zero: " << (*u_top_curr_ptr)[N_RHO-1][0] << std::endl;
    std::cout << "Side Init zero: " << (*u_side_curr_ptr)[0][NZ-1] << std::endl;
    
    const double L_top = 2.0 * M_PI * R;
    
    std::map<std::string, double> params_top = {
        {"R", R}, {"T", t_final}, {"dt", DT_2D_COMBINED}, {"N_steps", (double)n_steps},
        {"L", L_top}, {"H", R}, {"N_PHI", (double)N_PHI}, {"N_RHO", (double)N_RHO},
        {"D_PHI", D_PHI}, {"D_RHO", D_RHO},
        {"D_U", D_U}, {"CHI", CHI},
        {"ALPHA", ALPHA}, {"BETA", BETA}, {"GAMMA", 0.0}, {"W_0", W_0},
        {"SAVE_EVERY_T", SAVE_EVERY_T_2D_COMBINED}
    };
    
    std::map<std::string, double> params_side = {
        {"R", R}, {"T", t_final}, {"dt", DT_2D_COMBINED}, {"N_steps", (double)n_steps},
        {"L", L_CYL}, {"H", H}, {"N_PHI", (double)N_PHI}, {"NZ", (double)NZ},
        {"DX_CYL", DX_CYL}, {"DZ", DZ},
        {"D_U", D_U}, {"D_W", D_W}, {"CHI", CHI},
        {"ALPHA", ALPHA}, {"BETA", BETA}, {"GAMMA", GAMMA}, {"W_0", W_0},
        {"SAVE_EVERY_T", SAVE_EVERY_T_2D_COMBINED}
    };
    
    Writer writer_top("2_5D_combined_top", params_top);
    Writer writer_side("2_5D_combined_side", params_side);
    
    const std::string timestamp = makeTimestamp();
    
    std::string spatio_filename = "results/2_5D_combined_" + timestamp + "_spatiotemporal.dat";
    
    const double delta_rho_sq = D_RHO * D_RHO;
    const double inv_delta_rho_sq = 1.0 / delta_rho_sq;
    
    const double delta_phi_sq_1 = D_PHI * D_PHI;
    const double inv_delta_phi_sq_1 = 1.0 / delta_phi_sq_1;
    
    const double delta_phi_sq_2 = (2.0 * D_PHI) * (2.0 * D_PHI);
    const double inv_delta_phi_sq_2 = 1.0 / delta_phi_sq_2;
    
    const double delta_phi_sq_4 = (4.0 * D_PHI) * (4.0 * D_PHI);
    const double inv_delta_phi_sq_4 = 1.0 / delta_phi_sq_4;
    
    const double inv_dx_sq = 1.0 / (DX_CYL * DX_CYL);
    const double inv_dz_sq = 1.0 / (DZ * DZ);
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    std::cout << "Starting combined simulation with N_steps = " << n_steps << "\n";
    std::cout << "dt = " << DT_2D_COMBINED << ", T = " << t_final << "\n";
    std::cout << "Top grid: N_RHO = " << N_RHO << ", N_PHI = " << N_PHI << "\n";
    std::cout << "Side grid: N_PHI = " << N_PHI << ", NZ = " << NZ << "\n";
    std::cout << "Saving: Every " << SAVE_EVERY_T_2D_COMBINED << " time units (" << save_interval << " steps)\n";
    std::cout << "Spatiotemporal: Saving " << SPATIOTEMPORAL_SAMPLES << " time samples\n\n";
    
    std::cout << "Saving initial snapshots at t = 0.0\n";
    writer_top.saveSnapshot2Dtop(0.0, *u_top_curr_ptr);
    writer_side.saveSnapshot2Dside(0.0, *u_side_curr_ptr);
    
    for (int step = 0; step <= n_steps; ++step) {
        double t = step * DT_2D_COMBINED;

        auto& u_top_curr = *u_top_curr_ptr;
        auto& v_top_curr = *v_top_curr_ptr;
        auto& u_top_nxt  = *u_top_next_ptr;
        auto& v_top_nxt  = *v_top_next_ptr;
        auto& u_side_curr = *u_side_curr_ptr;
        auto& v_side_curr = *v_side_curr_ptr;
        auto& w_side_curr = *w_side_curr_ptr;
        auto& u_side_nxt  = *u_side_next_ptr;
        auto& v_side_nxt  = *v_side_next_ptr;
        auto& w_side_nxt  = *w_side_next_ptr;
        
        if (step % progress_interval == 0) {
            double max_u_top = 0.0;
            for (const auto& row : u_top_curr) {
                max_u_top = std::max(max_u_top, *std::max_element(row.begin(), row.end()));
            }
            double max_U_side = 0.0;
            for (const auto& row : u_side_curr) {
                max_U_side = std::max(max_U_side, *std::max_element(row.begin(), row.end()));
            }
            std::cout << "step = " << step << " (t = " << t << "), max(u_top_current) = " << max_u_top 
                      << ", max(u_side_current) = " << max_U_side << "\n";
        }
        
        if (step % spatiotemporal_interval == 0) {
            vector<double> avg_values(N_PHI, 0.0);
            const int points_count = 5;
            for (int p = 0; p < N_PHI; ++p) {
                double sum = 0.0;

                // 2 rows below junction in side domain (not including junction itself)
                sum += u_side_curr[p][NZ - 3];  // 2 rows before junction
                sum += u_side_curr[p][NZ - 2];  // 1 row before junction

                // Junction row itself (shared boundary - take from either, they must be equal)
                sum += u_top_curr[N_RHO - 1][p];

                // 2 rows into top domain from junction
                sum += u_top_curr[N_RHO - 2][p];  // 1 row into top
                sum += u_top_curr[N_RHO - 3][p];  // 2 rows into top

                avg_values[p] = sum / points_count;
            }
            spatiotemporal_data.push_back(avg_values);
        }
        
        // =============================
        // UPDATE TOP DOMAIN
        // =============================
        
        #pragma omp parallel for schedule(static, 2)
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
                
                double u_rho_phi = u_top_curr[rho][phi];
                double u_rho_plus_1_phi = u_top_curr[rho + 1][phi];
                double u_rho_minus_1_phi = u_top_curr[rho - 1][phi];
                double u_rho_phi_plus = u_top_curr[rho][phi_plus];
                double u_rho_phi_minus = u_top_curr[rho][phi_minus];
                
                double v_rho_phi = v_top_curr[rho][phi];
                double v_rho_plus_1_phi = v_top_curr[rho + 1][phi];
                double v_rho_minus_1_phi = v_top_curr[rho - 1][phi];
                double v_rho_phi_plus = v_top_curr[rho][phi_plus];
                double v_rho_phi_minus = v_top_curr[rho][phi_minus];
                
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
                
                u_top_nxt[rho][phi] = u_rho_phi + DT_2D_COMBINED * dudt;
                
                double diff_v_radial = inv_rho_i * (
                    (rho_plus_half * (v_rho_plus_1_phi - v_rho_phi) -
                     rho_minus_half * (v_rho_phi - v_rho_minus_1_phi)) * inv_delta_rho_sq
                );
                
                double diff_v_angular = inv_rho_i_sq * (
                    (v_rho_phi_plus - 2.0 * v_rho_phi + v_rho_phi_minus) * inv_dphi_sq_local
                );
                
                double prod_v = (u_rho_phi / (1.0 + BETA * u_rho_phi)) - v_rho_phi;
                
                double dvdt = (diff_v_radial + diff_v_angular) + prod_v;
                
                v_top_nxt[rho][phi] = v_rho_phi + DT_2D_COMBINED * dvdt;
            }
        }
        
        fillMissingPhiValues(u_top_nxt);
        fillMissingPhiValues(v_top_nxt);
        
        #pragma omp parallel for schedule(static)
        for (int phi = 0; phi < N_PHI / 2; ++phi) {
            int phi_opp = phi + N_PHI / 2;
            double u_avg = 0.5 * (u_top_nxt[1][phi] + u_top_nxt[1][phi_opp]);
            double v_avg = 0.5 * (v_top_nxt[1][phi] + v_top_nxt[1][phi_opp]);
            u_top_nxt[0][phi] = u_avg;
            u_top_nxt[0][phi_opp] = u_avg;
            v_top_nxt[0][phi] = v_avg;
            v_top_nxt[0][phi_opp] = v_avg;
        }
        
        #pragma omp parallel for schedule(static)
        for (int phi = 0; phi < N_PHI; ++phi) {
            u_top_nxt[N_RHO - 1][phi] = u_top_nxt[N_RHO - 2][phi];
            v_top_nxt[N_RHO - 1][phi] = v_top_nxt[N_RHO - 2][phi];
        }
        
        // =============================
        // UPDATE SIDE DOMAIN
        // =============================
        
        #pragma omp parallel for collapse(2) schedule(static)
        for (int i = 0; i < N_PHI; ++i) {
            for (int j = 1; j < NZ - 1; ++j) {
                int i_plus = wrapPhi(i + 1);
                int i_minus = wrapPhi(i - 1);
                int j_plus = j + 1;
                int j_minus = j - 1;
                
                double U_xp = u_side_curr[i_plus][j];
                double U_xm = u_side_curr[i_minus][j];
                double U_zp = u_side_curr[i][j_plus];
                double U_zm = u_side_curr[i][j_minus];
                double U_ij = u_side_curr[i][j];
                
                double V_xp = v_side_curr[i_plus][j];
                double V_xm = v_side_curr[i_minus][j];
                double V_zp = v_side_curr[i][j_plus];
                double V_zm = v_side_curr[i][j_minus];
                double V_ij = v_side_curr[i][j];
                
                double W_xp = w_side_curr[i_plus][j];
                double W_xm = w_side_curr[i_minus][j];
                double W_zp = w_side_curr[i][j_plus];
                double W_zm = w_side_curr[i][j_minus];
                double W_ij = w_side_curr[i][j];
                
                double du = D_U * (
                    (U_xp + U_xm - 2.0 * U_ij) * inv_dx_sq +
                    (U_zp + U_zm - 2.0 * U_ij) * inv_dz_sq
                );
                
                double eq1 = (
                    (U_xp + U_ij) * 0.5 * (V_xp - V_ij) -
                    (U_ij + U_xm) * 0.5 * (V_ij - V_xm)
                ) * inv_dx_sq;
                
                double eq2 = (
                    (U_zp + U_ij) * 0.5 * (V_zp - V_ij) -
                    (U_ij + U_zm) * 0.5 * (V_ij - V_zm)
                ) * inv_dz_sq;
                
                double chi = CHI * (eq1 + eq2);
                double alpha = ALPHA * U_ij * (1.0 - U_ij / W_ij);
                
                u_side_nxt[i][j] = U_ij + DT_2D_COMBINED * (du - chi + alpha);
                
                double dv = (
                    (V_xp + V_xm - 2.0 * V_ij) * inv_dx_sq +
                    (V_zp + V_zm - 2.0 * V_ij) * inv_dz_sq
                );
                double beta = (U_ij / (1.0 + BETA * U_ij)) - V_ij;
                
                v_side_nxt[i][j] = V_ij + DT_2D_COMBINED * (dv + beta);
                
                double dw = D_W * (
                    (W_xp + W_xm - 2.0 * W_ij) * inv_dx_sq +
                    (W_zp + W_zm - 2.0 * W_ij) * inv_dz_sq
                );
                double gamma = GAMMA * U_ij;
                
                w_side_nxt[i][j] = W_ij + DT_2D_COMBINED * (dw - gamma);
            }
        }
        
        #pragma omp parallel for schedule(static)
        for (int i = 0; i < N_PHI; ++i) {
            u_side_nxt[i][NZ - 1] = u_side_nxt[i][NZ - 2];
            v_side_nxt[i][NZ - 1] = v_side_nxt[i][NZ - 2];
            w_side_nxt[i][NZ - 1] = W_0;
            u_side_nxt[i][0] = u_side_nxt[i][1];
            v_side_nxt[i][0] = v_side_nxt[i][1];
            w_side_nxt[i][0] = w_side_nxt[i][1];
        }
        
        // =============================
        // INTERFACE COUPLING
        // =============================
        
        #pragma omp parallel for schedule(static)
        for (int phi = 0; phi < N_PHI; ++phi) {
            int phi_plus  = wrapPhi(phi + 1);
            int phi_minus = wrapPhi(phi - 1);
        
            double u_c = u_top_curr[N_RHO - 1][phi];
            double v_c = v_top_curr[N_RHO - 1][phi];

            double u_rho_inner = u_top_curr[N_RHO - 2][phi];
            double v_rho_inner = v_top_curr[N_RHO - 2][phi];
        
            double u_z_below = u_side_curr[phi][NZ - 2];
            double v_z_below = v_side_curr[phi][NZ - 2];
        
            double u_phi_p = u_top_curr[N_RHO - 1][phi_plus];
            double u_phi_m = u_top_curr[N_RHO - 1][phi_minus];
            double v_phi_p = v_top_curr[N_RHO - 1][phi_plus];
            double v_phi_m = v_top_curr[N_RHO - 1][phi_minus];
        
            const double rho_R = (N_RHO - 1) * D_RHO;
            const double rho_R_half = rho_R - 0.5 * D_RHO;
            const double inv_rho_R = 1.0 / rho_R;
            const double inv_rho_R_sq = inv_rho_R * inv_rho_R;
        
            double diff_u_radial = inv_rho_R * inv_delta_rho_sq * rho_R_half * (u_rho_inner - u_c);
            double diff_v_radial = inv_rho_R * inv_delta_rho_sq * rho_R_half * (v_rho_inner - v_c);
            double diff_u_angular = inv_rho_R_sq * inv_delta_phi_sq_1 * (u_phi_p - 2.0 * u_c + u_phi_m);
            double diff_v_angular = inv_rho_R_sq * inv_delta_phi_sq_1 * (v_phi_p - 2.0 * v_c + v_phi_m);
            double diff_u_z = (u_z_below - u_c) * inv_dz_sq;
            double diff_v_z = (v_z_below - v_c) * inv_dz_sq;
        
            double chem_u_radial = inv_rho_R * inv_delta_rho_sq * rho_R_half * 0.5 * (u_rho_inner + u_c) * (v_rho_inner - v_c);
            double chem_u_angular = inv_rho_R_sq * inv_delta_phi_sq_1 * (
                0.5 * (u_phi_p + u_c) * (v_phi_p - v_c)
                - 0.5 * (u_c + u_phi_m) * (v_c - v_phi_m)
            );
            double chem_u_z = inv_dz_sq * 0.5 * (u_z_below + u_c) * (v_z_below - v_c);
        
            double reaction_u = ALPHA * u_c * (1.0 - u_c);
            double prod_v = (u_c / (1.0 + BETA * u_c)) - v_c;
        
            double u_interface = u_c + DT_2D_COMBINED * (
                D_U * (diff_u_radial + diff_u_angular + diff_u_z)
                - CHI  * (chem_u_radial + chem_u_angular + chem_u_z)
                + reaction_u
            );
        
            double v_interface = v_c + DT_2D_COMBINED * (
                1.0 * (diff_v_radial + diff_v_angular + diff_v_z) + prod_v
            );

            u_top_nxt[N_RHO - 1][phi] = u_interface;
            v_top_nxt[N_RHO - 1][phi] = v_interface;
            u_side_nxt[phi][NZ - 1] = u_interface;
            v_side_nxt[phi][NZ - 1] = v_interface;
        }
        
        std::swap(u_top_curr_ptr, u_top_next_ptr);
        std::swap(v_top_curr_ptr, v_top_next_ptr);
        std::swap(u_side_curr_ptr, u_side_next_ptr);
        std::swap(v_side_curr_ptr, v_side_next_ptr);
        std::swap(w_side_curr_ptr, w_side_next_ptr);
        
        if (step % save_interval == 0) {
            std::cout << "Saving snapshots at t = " << t << "\n";
            writer_top.saveSnapshot2Dtop(t, *u_top_curr_ptr);
            writer_side.saveSnapshot2Dside(t, *u_side_curr_ptr);
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end_time - start_time;
    
    std::cout << "\n===== SIMULATION COMPLETE =====\n";
    std::cout << "Total time: " << elapsed.count() << " seconds\n";
        
    saveSpatiotemporalData(spatio_filename, spatiotemporal_data, t_final, std::to_string(L_CYL), "2D combined - calculated over edge");
    
    double u_top_min = std::numeric_limits<double>::infinity();
    double u_top_max = -std::numeric_limits<double>::infinity();
    double u_side_min = std::numeric_limits<double>::infinity();
    double u_side_max = -std::numeric_limits<double>::infinity();
    bool has_nan = false;
    
    auto& u_top_final = *u_top_curr_ptr;
    auto& u_side_final = *u_side_curr_ptr;

    #pragma omp parallel for reduction(min:u_top_min) reduction(max:u_top_max) schedule(static)
    for (int r = 0; r < N_RHO; ++r) {
        for (int p = 0; p < N_PHI; ++p) {
            if (std::isnan(u_top_final[r][p])) has_nan = true;
            u_top_min = min(u_top_min, u_top_final[r][p]);
            u_top_max = max(u_top_max, u_top_final[r][p]);
        }
    }

    #pragma omp parallel for reduction(min:u_side_min) reduction(max:u_side_max) schedule(static)
    for (int i = 0; i < N_PHI; ++i) {
        for (int j = 0; j < NZ; ++j) {
            if (std::isnan(u_side_final[i][j])) has_nan = true;
            u_side_min = min(u_side_min, u_side_final[i][j]);
            u_side_max = max(u_side_max, u_side_final[i][j]);
        }
    }
    
    std::cout << "Final u_top_current: min = " << u_top_min << ", max = " << u_top_max << "\n";
    std::cout << "Final u_side_current: min = " << u_side_min << ", max = " << u_side_max << "\n";
    
    if (has_nan) {
        std::cout << "WARNING: NaN detected in solution!\n";
    } else {
        std::cout << "No NaN detected.\n";
    }
    
    return 0;
}