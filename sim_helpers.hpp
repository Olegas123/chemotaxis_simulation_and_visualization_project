#ifndef SIM_HELPERS_HPP
#define SIM_HELPERS_HPP
 
#include "constants.hpp"
 
#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <ctime>

inline int wrapPhi(int phi) {
    int p = phi % N_PHI;
    return (p < 0) ? p + N_PHI : p;
}

inline std::string makeTimestamp() {
    std::time_t now = std::time(nullptr);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%Y%m%d_%H%M%S", std::localtime(&now));
    return std::string(buf);
}
 
inline void fillMissingPhiValues(std::vector<std::vector<double>>& u) {
    for (int rho = 0; rho < N_RHO; ++rho) {
        int phiInc = 1;
        if (rho < RHO_HALF)    phiInc = 2;
        if (rho < RHO_QUARTER) phiInc = 4;
        if (phiInc == 1) continue;
 
        for (int phi = 0; phi < N_PHI; ++phi) {
            if (phi % phiInc == 0) continue;
            int phiL = (phi / phiInc) * phiInc;
            int phiR = (phiL + phiInc) % N_PHI;
            u[rho][phi] = 0.5 * (u[rho][phiL] + u[rho][phiR]);
        }
    }
}
 
inline void saveSpatiotemporalData(
        const std::string& filename,
        const std::vector<std::vector<double>>& data,
        double T_total,
        const std::string& L_total,
        const std::string& description) {
 
    std::ofstream file(filename);
    if (!file.is_open()) {
        std::cerr << "ERROR: Cannot open spatiotemporal file: " << filename << "\n";
        return;
    }
    file << std::fixed;
    file.precision(6);
 
    file << "# Spatiotemporal data — " << description << "\n";
    file << "# N_PHI = "      << N_PHI        << "\n";
    file << "# NT_samples = " << data.size()  << "\n";
    file << "# T = "          << T_total      << "\n";
    file << "# L = "          << L_total      << "\n";
    file << "# Format: each row = one time sample, columns = phi positions\n";
    file << "#\n";
 
    for (const auto& row : data) {
        for (int i = 0; i < N_PHI; ++i) {
            file << row[i];
            if (i < N_PHI - 1) file << " ";
        }
        file << "\n";
    }
 
    file.close();
    std::cout << "Saved spatiotemporal data to: " << filename << "\n"
              << "  Time samples: "  << data.size()  << "\n"
              << "  Spatial points: " << N_PHI        << "\n";
}
 
#endif // SIM_HELPERS_HPP
 