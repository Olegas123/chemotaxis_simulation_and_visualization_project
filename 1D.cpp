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

void initializeRandom(vector<double>& u) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    
    for (auto& val : u) {
        val = dist(gen);
    }
}

int main(int argc, char* argv[]) {
    std::cout << std::fixed << std::setprecision(6);
    SIM_INIT(argc, argv, DT_1D, SAVE_EVERY_T_1D);

    #ifdef _OPENMP
    omp_set_num_threads(OPEN_MP_THREAD_COUNT);
    #else
    std::cout << "WARNING: OpenMP not enabled! Recompile with -fopenmp\n";
    #endif
    
    vector<double> u_current(N_PHI, 0.0);
    vector<double> u_next(N_PHI, 0.0);
    vector<double> v_current(N_PHI, 0.0);
    vector<double> v_next(N_PHI, 0.0);

    auto* u_curr_ptr = &u_current;
    auto* u_next_ptr = &u_next;
    auto* v_curr_ptr = &v_current;
    auto* v_next_ptr = &v_next;
    
    vector<vector<double>> spatiotemporal_data;
    spatiotemporal_data.reserve(SPATIOTEMPORAL_SAMPLES);
    int spatiotemporal_interval = std::max(1, n_steps / SPATIOTEMPORAL_SAMPLES);
    
    if (!ic_file.empty()) {
        std::cout << "Loading initial conditions from: " << ic_file << "\n";
        if (!load1DInitialConditions(ic_file, *u_curr_ptr, N_PHI)) {
            std::cerr << "Failed to load IC, using random instead\n";
            initializeRandom(*u_curr_ptr);
        }
    } else {
        std::cout << "No IC file provided, using random initialization\n";
        initializeRandom(*u_curr_ptr);
    }
    
    std::cout << "Init zero: " << (*u_curr_ptr)[0] << std::endl;
    
    std::map<std::string, double> params = {
        {"D_U", D_U}, {"CHI", CHI}, {"ALPHA", ALPHA}, {"BETA", BETA},
        {"L", L_1D}, {"T", t_final}, {"dx", DX_1D}, {"dt", DT_1D},
        {"N_PHI", (double)N_PHI}, {"N_STEPS", (double)n_steps},
        {"SAVE_EVERY_T", SAVE_EVERY_T_1D}
    };
    
    Writer writer("1D", params);
    
    const std::string timestamp = makeTimestamp();
    
    std::string spatio_filename = "results/1D_" + timestamp + "_spatiotemporal.dat";
    
    const double deltax_sq = DX_1D * DX_1D;
    const double inv_deltax_sq = 1.0 / deltax_sq;
    const double inv_2deltax_sq = 1.0 / (2.0 * deltax_sq);
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    std::cout << "===== 1D MODEL SIMULATION =====\n";
    std::cout << "Grid: " << N_PHI << " points, L = " << L_1D << "\n";
    std::cout << "Time: " << n_steps << " steps, T = " << t_final << ", dt = " << DT_1D << "\n";
    std::cout << "Parameters: D_U = " << D_U << ", CHI = " << CHI << "\n";
    std::cout << "            ALPHA = " << ALPHA << ", BETA = " << BETA << "\n";
    std::cout << "Saving: Every " << SAVE_EVERY_T_1D << " time units (" << save_interval << " steps)\n";
    std::cout << "Spatiotemporal: Saving " << SPATIOTEMPORAL_SAMPLES << " time samples\n\n";

    double last_save_time = 0.0;
    
    for (int i = 0; i < n_steps; ++i) {
        double current_time = i * DT_1D;

        auto& u_curr = *u_curr_ptr;
        auto& v_curr = *v_curr_ptr;
        auto& u_nxt  = *u_next_ptr;
        auto& v_nxt  = *v_next_ptr;
        
        if (i % progress_interval == 0) {
            double max_u = *std::max_element(u_curr.begin(), u_curr.end());
            std::cout << "step = " << i << " (t = " << current_time 
                      << "), max(u) = " << max_u << "\n";
        }
        
        if (i % spatiotemporal_interval == 0) {
            spatiotemporal_data.push_back(u_curr);
        }
        
        #pragma omp parallel for schedule(static)
        for (int x = 0; x < N_PHI; ++x) {
            int x_left = (x - 1 + N_PHI) % N_PHI;
            int x_right = (x + 1) % N_PHI;
            
            double u_c = u_curr[x];
            double u_left = u_curr[x_left];
            double u_right = u_curr[x_right];
            
            double v_c = v_curr[x];
            double v_left = v_curr[x_left];
            double v_right = v_curr[x_right];
            
            double term1_1 = D_U * (u_right - 2.0 * u_c + u_left) * inv_deltax_sq;
            
            double term1_2 = CHI * (((u_right + u_c) * (v_right - v_c) -
                                     (u_c) * (v_c - v_left)) * inv_2deltax_sq);
            
            double term1_3 = ALPHA * u_c * (1.0 - u_c);
            
            u_nxt[x] = u_c + DT_1D * (term1_1 - term1_2 + term1_3);
            
            double term2_1 = (v_right - 2.0 * v_c + v_left) * inv_deltax_sq;
            double term2_2 = u_c / (1.0 + BETA * u_c) - v_c;
            
            v_nxt[x] = v_c + DT_1D * (term2_1 + term2_2);
        }
        
        std::swap(u_curr_ptr, u_next_ptr);
        std::swap(v_curr_ptr, v_next_ptr);
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end_time - start_time;
    
    std::cout << "\n===== SIMULATION COMPLETE =====\n";
    std::cout << "Total time: " << elapsed.count() << " seconds\n";
    
    saveSpatiotemporalData(spatio_filename, spatiotemporal_data, t_final, std::to_string(L_CYL), "1D model");
    
    auto& u_final = *u_curr_ptr;
    double u_min = std::numeric_limits<double>::infinity();
    double u_max = -std::numeric_limits<double>::infinity();

    #pragma omp parallel for reduction(min:u_min) reduction(max:u_max) schedule(static)
    for (int x = 0; x < N_PHI; ++x) {
        u_min = std::min(u_min, u_final[x]);
        u_max = std::max(u_max, u_final[x]);
    }
    
    std::cout << "Final u: min = " << u_min << ", max = " << u_max << "\n";
    
    return 0;
}