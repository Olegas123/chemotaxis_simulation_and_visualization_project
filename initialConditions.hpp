#ifndef IC_LOADER_HPP
#define IC_LOADER_HPP

#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <iostream>


inline bool load1DInitialConditions(const std::string& filename, 
                                    std::vector<double>& U, 
                                    int NX) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        std::cerr << "ERROR: Cannot open IC file: " << filename << "\n";
        return false;
    }
    
    std::cout << "Loading 1D initial conditions from: " << filename << "\n";
    
    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;
        break;
    }
    
    std::istringstream iss(line);
    for (int x = 0; x < NX; ++x) {
        double val;
        if (!(iss >> val)) {
            std::cerr << "ERROR: Failed to read value at x=" << x << "\n";
            return false;
        }
        U[x] = val;
    }
    
    file.close();
    
    std::cout << "✓ Successfully loaded 1D initial conditions\n";
    std::cout << "  Grid: " << NX << " points\n";
    
    double sum = 0.0, min_val = U[0], max_val = U[0];
    for (int x = 0; x < NX; ++x) {
        double val = U[x];
        sum += val;
        if (val < min_val) min_val = val;
        if (val > max_val) max_val = val;
    }
    double mean = sum / NX;
    
    std::cout << "  Range: [" << min_val << ", " << max_val << "]\n";
    std::cout << "  Mean: " << mean << "\n";
    
    return true;
}


inline bool load2DPolarInitialConditions(const std::string& filename,
                                         std::vector<std::vector<double>>& U,
                                         int ERDVE_RHO, int ERDVE_PHI) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        std::cerr << "ERROR: Cannot open IC file: " << filename << "\n";
        return false;
    }
    
    std::cout << "Loading 2D polar initial conditions from: " << filename << "\n";
    
    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;
        break;
    }
    
    for (int r = 0; r < ERDVE_RHO; ++r) {
        if (r > 0) {
            if (!std::getline(file, line)) {
                std::cerr << "ERROR: Unexpected end of file at rho=" << r << "\n";
                return false;
            }
        }
        
        std::istringstream iss(line);
        for (int p = 0; p < ERDVE_PHI; ++p) {
            double val;
            if (!(iss >> val)) {
                std::cerr << "ERROR: Failed to read value at rho=" << r << ", phi=" << p << "\n";
                return false;
            }
            U[r][p] = val;
        }
    }
    
    file.close();
    
    std::cout << "✓ Successfully loaded 2D polar initial conditions\n";
    std::cout << "  Grid: " << ERDVE_RHO << " x " << ERDVE_PHI << "\n";
    
    double sum = 0.0, min_val = U[0][0], max_val = U[0][0];
    for (int r = 0; r < ERDVE_RHO; ++r) {
        for (int p = 0; p < ERDVE_PHI; ++p) {
            double val = U[r][p];
            sum += val;
            if (val < min_val) min_val = val;
            if (val > max_val) max_val = val;
        }
    }
    double mean = sum / (ERDVE_RHO * ERDVE_PHI);
    
    std::cout << "  Range: [" << min_val << ", " << max_val << "]\n";
    std::cout << "  Mean: " << mean << "\n";
    
    return true;
}


inline bool load2DCylindricalInitialConditions(const std::string& filename,
                                               std::vector<std::vector<double>>& U,
                                               int N_PHI, int NZ) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        std::cerr << "ERROR: Cannot open IC file: " << filename << "\n";
        return false;
    }
    
    std::cout << "Loading 2D cylindrical initial conditions from: " << filename << "\n";
    
    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;
        break;
    }
    
    for (int p = 0; p < N_PHI; ++p) {
        if (p > 0) {
            if (!std::getline(file, line)) {
                std::cerr << "ERROR: Unexpected end of file at phi=" << p << "\n";
                return false;
            }
        }
        
        std::istringstream iss(line);
        for (int z = 0; z < NZ; ++z) {
            double val;
            if (!(iss >> val)) {
                std::cerr << "ERROR: Failed to read value at phi=" << p << ", z=" << z << "\n";
                return false;
            }
            U[p][z] = val;
        }
    }
    
    file.close();
    
    std::cout << "✓ Successfully loaded 2D cylindrical initial conditions\n";
    std::cout << "  Grid: " << N_PHI << " x " << NZ << "\n";
    
    double sum = 0.0, min_val = U[0][0], max_val = U[0][0];
    for (int p = 0; p < N_PHI; ++p) {
        for (int z = 0; z < NZ; ++z) {
            double val = U[p][z];
            sum += val;
            if (val < min_val) min_val = val;
            if (val > max_val) max_val = val;
        }
    }
    double mean = sum / (N_PHI * NZ);
    
    std::cout << "  Range: [" << min_val << ", " << max_val << "]\n";
    std::cout << "  Mean: " << mean << "\n";
    
    return true;
}


inline bool load3DInitialConditions(const std::string& filename,
                                    std::vector<std::vector<std::vector<double>>>& U,
                                    int ERDVE_RHO, int ERDVE_PHI, int NZ) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        std::cerr << "ERROR: Cannot open IC file: " << filename << "\n";
        return false;
    }
    
    std::cout << "Loading 3D initial conditions from: " << filename << "\n";
    
    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;
        break;
    }
    
    for (int rho = 0; rho < ERDVE_RHO; ++rho) {
        for (int z = 0; z < NZ; ++z) {
            if (rho > 0 || z > 0) {
                if (!std::getline(file, line)) {
                    std::cerr << "ERROR: Unexpected end of file at rho=" << rho << ", z=" << z << "\n";
                    return false;
                }
            }
            
            std::istringstream iss(line);
            for (int phi = 0; phi < ERDVE_PHI; ++phi) {
                double val;
                if (!(iss >> val)) {
                    std::cerr << "ERROR: Failed to read value at rho=" << rho << ", phi=" << phi << ", z=" << z << "\n";
                    return false;
                }
                U[rho][phi][z] = val;
            }
        }
    }
    
    file.close();
    
    std::cout << "✓ Successfully loaded 3D initial conditions\n";
    std::cout << "  Grid: " << ERDVE_RHO << " x " << ERDVE_PHI << " x " << NZ << "\n";
    
    double sum = 0.0, min_val = U[0][0][0], max_val = U[0][0][0];
    for (int r = 0; r < ERDVE_RHO; ++r) {
        for (int p = 0; p < ERDVE_PHI; ++p) {
            for (int z = 0; z < NZ; ++z) {
                double val = U[r][p][z];
                sum += val;
                if (val < min_val) min_val = val;
                if (val > max_val) max_val = val;
            }
        }
    }
    double mean = sum / (ERDVE_RHO * ERDVE_PHI * NZ);
    
    std::cout << "  Range: [" << min_val << ", " << max_val << "]\n";
    std::cout << "  Mean: " << mean << "\n";
    
    return true;
}

#endif // IC_LOADER_HPP