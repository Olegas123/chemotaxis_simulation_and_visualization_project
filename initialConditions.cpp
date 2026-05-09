#include "constants.hpp"
#include <iostream>
#include <fstream>
#include <vector>
#include <cmath>
#include <random>
#include <iomanip>
#include <string>

using std::vector;
using std::string;

const double IC_MIN = 0.5;
const double IC_MAX = 1.5;


void generate3DInitialConditions(const string& filename) {
    std::cout << "Generating 3D initial conditions...\n";
    std::cout << "Grid: " << N_RHO << " x " << N_PHI << " x " << NZ << "\n";
    std::cout << "Using parameters from constants.hpp\n";
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<double> dist(IC_MIN, IC_MAX);
    
    vector<vector<vector<double>>> U(N_RHO, vector<vector<double>>(N_PHI, vector<double>(NZ, 0.0)));
    
    for (int r = 0; r < N_RHO; ++r) {
        for (int p = 0; p < N_PHI; ++p) {
            for (int z = 0; z < NZ; ++z) {
                U[r][p][z] = dist(gen);
            }
        }
    }
    
    std::ofstream file(filename);
    if (!file.is_open()) {
        std::cerr << "ERROR: Cannot open file: " << filename << "\n";
        return;
    }
    
    file << std::fixed << std::setprecision(6);
    
    file << "# 3D Initial Conditions\n";
    file << "# Generated using initialConditions.cpp\n";
    file << "# N_RHO = " << N_RHO << "\n";
    file << "# N_PHI = " << N_PHI << "\n";
    file << "# NZ = " << NZ << "\n";
    file << "# R = " << R << "\n";
    file << "# H = " << H << "\n";
    file << "# IC distribution: Uniform [" << IC_MIN << ", " << IC_MAX << "]\n";
    file << "#\n";
    file << "# Data format: For each rho, for each z, write all phi values on one line\n";
    file << "#\n";
    
    for (int r = 0; r < N_RHO; ++r) {
        for (int z = 0; z < NZ; ++z) {
            for (int p = 0; p < N_PHI; ++p) {
                file << U[r][p][z];
                if (p < N_PHI - 1) file << " ";
            }
            file << "\n";
        }
    }
    
    file.close();
    
    std::cout << "✓ Saved 3D initial conditions to: " << filename << "\n";
    std::cout << "  Total points: " << (N_RHO * N_PHI * NZ) << "\n";
    
    double sum = 0.0, min_val = U[0][0][0], max_val = U[0][0][0];
    
    for (int r = 0; r < N_RHO; ++r) {
        for (int p = 0; p < N_PHI; ++p) {
            for (int z = 0; z < NZ; ++z) {
                double val = U[r][p][z];
                sum += val;
                if (val < min_val) min_val = val;
                if (val > max_val) max_val = val;
            }
        }
    }
    
    double mean = sum / (N_RHO * N_PHI * NZ);
    
    std::cout << "  Statistics: Min=" << min_val << ", Max=" << max_val << ", Mean=" << mean << "\n";
}


void extractPolar2D(const string& input_file, const string& output_file) {
    std::cout << "Extracting 2D polar IC from 3D (top disk at z=H)...\n";
    
    std::ifstream infile(input_file);
    if (!infile.is_open()) {
        std::cerr << "ERROR: Cannot open input file: " << input_file << "\n";
        return;
    }
    
    string line;
    while (std::getline(infile, line)) {
        if (line.empty() || line[0] == '#') continue;
        break;
    }
    
    vector<vector<double>> U_polar(N_RHO, vector<double>(N_PHI, 0.0));
    
    for (int r = 0; r < N_RHO; ++r) {
        for (int z = 0; z < NZ - 1; ++z) {
            if (r == 0 && z == 0) {
                continue;
            }
            if (!std::getline(infile, line)) {
                std::cerr << "ERROR: Unexpected EOF at r=" << r << ", z=" << z << "\n";
                return;
            }
        }
        
        if (r > 0 || NZ > 1) {
            if (!std::getline(infile, line)) {
                std::cerr << "ERROR: Unexpected EOF at r=" << r << ", z=" << (NZ-1) << "\n";
                return;
            }
        }
        
        std::istringstream iss(line);
        for (int p = 0; p < N_PHI; ++p) {
            if (!(iss >> U_polar[r][p])) {
                std::cerr << "ERROR: Failed to read r=" << r << ", phi=" << p << "\n";
                return;
            }
        }
    }
    
    infile.close();
    
    std::ofstream outfile(output_file);
    if (!outfile.is_open()) {
        std::cerr << "ERROR: Cannot open output file: " << output_file << "\n";
        return;
    }
    
    outfile << std::fixed << std::setprecision(6);
    
    outfile << "# 2D Polar Initial Conditions (extracted from 3D at z=H)\n";
    outfile << "# N_RHO = " << N_RHO << "\n";
    outfile << "# N_PHI = " << N_PHI << "\n";
    outfile << "# R = " << R << "\n";
    outfile << "#\n";
    
    for (int r = 0; r < N_RHO; ++r) {
        for (int p = 0; p < N_PHI; ++p) {
            outfile << U_polar[r][p];
            if (p < N_PHI - 1) outfile << " ";
        }
        outfile << "\n";
    }
    
    outfile.close();
    
    std::cout << "✓ Saved 2D polar IC to: " << output_file << "\n";
    std::cout << "  Grid: " << N_RHO << " x " << N_PHI << "\n";
}


void extractCylindrical2D(const string& input_file, const string& output_file) {
    std::cout << "Extracting 2D cylindrical IC from 3D (outer surface at r=R)...\n";
    
    std::ifstream infile(input_file);
    if (!infile.is_open()) {
        std::cerr << "ERROR: Cannot open input file: " << input_file << "\n";
        return;
    }
    
    string line;
    while (std::getline(infile, line)) {
        if (line.empty() || line[0] == '#') continue;
        break;
    }
    
    vector<vector<double>> U_cyl(N_PHI, vector<double>(NZ, 0.0));

    for (int r = 0; r < N_RHO - 1; ++r) {
        for (int z = 0; z < NZ; ++z) {
            if (r == 0 && z == 0) {
                // First line already in 'line', skip it
            } else {
                std::getline(infile, line);
            }
        }
    }
    
    for (int z = 0; z < NZ; ++z) {
        if (N_RHO > 1 || z > 0) {
            std::getline(infile, line);
        }
        std::istringstream iss(line);
        for (int p = 0; p < N_PHI; ++p) {
            iss >> U_cyl[p][z];
        }
    }
    
    infile.close();
    
    // Write output
    std::ofstream outfile(output_file);
    if (!outfile.is_open()) {
        std::cerr << "ERROR: Cannot open output file: " << output_file << "\n";
        return;
    }
    
    outfile << std::fixed << std::setprecision(6);
    
    outfile << "# 2D Cylindrical Initial Conditions (extracted from 3D at r=R)\n";
    outfile << "# N_PHI = " << N_PHI << " (angular points)\n";
    outfile << "# NZ = " << NZ << " (vertical points)\n";
    outfile << "# R = " << R << "\n";
    outfile << "# H = " << H << "\n";
    outfile << "#\n";
    
    for (int p = 0; p < N_PHI; ++p) {
        for (int z = 0; z < NZ; ++z) {
            outfile << U_cyl[p][z];
            if (z < NZ - 1) outfile << " ";
        }
        outfile << "\n";
    }
    
    outfile.close();
    
    std::cout << "✓ Saved 2D cylindrical IC to: " << output_file << "\n";
    std::cout << "  Grid: " << N_PHI << " x " << NZ << "\n";
}


void extract1D(const string& input_file, const string& output_file) {
    std::cout << "Extracting 1D IC from 3D (outer edge at top, r=R, z=H)...\n";
    
    std::ifstream infile(input_file);
    if (!infile.is_open()) {
        std::cerr << "ERROR: Cannot open input file: " << input_file << "\n";
        return;
    }
    
    string line;
    while (std::getline(infile, line)) {
        if (line.empty() || line[0] == '#') continue;
        break;
    }
    
    vector<double> U_1d(N_PHI, 0.0);
    
    int target_rho = N_RHO - 1;
    int target_z = NZ - 1;
    
    int target_line = target_rho * NZ + target_z;
    
    std::cout << "  Target: r=" << target_rho << ", z=" << target_z << "\n";
    std::cout << "  Target line number: " << target_line << " (0-indexed)\n";
    
    for (int i = 0; i < target_line; ++i) {
        if (!std::getline(infile, line)) {
            std::cerr << "ERROR: Unexpected EOF at line " << i << "\n";
            return;
        }
    }
    
    std::cout << "  First few values: " << line.substr(0, 60) << "...\n";
    
    std::istringstream iss(line);
    for (int p = 0; p < N_PHI; ++p) {
        if (!(iss >> U_1d[p])) {
            std::cerr << "ERROR: Failed to read phi=" << p << "\n";
            return;
        }
    }
    
    infile.close();
    
    std::ofstream outfile(output_file);
    if (!outfile.is_open()) {
        std::cerr << "ERROR: Cannot open output file: " << output_file << "\n";
        return;
    }
    
    outfile << std::fixed << std::setprecision(6);
    
    outfile << "# 1D Initial Conditions (extracted from 3D at r=R, z=H)\n";
    outfile << "# This is the outer edge at the top - where polar disk meets cylinder\n";
    outfile << "# N_PHI = " << N_PHI << "\n";
    outfile << "# L = " << (2.0 * M_PI * R) << " (circumference at r=R)\n";
    outfile << "#\n";
    
    for (int p = 0; p < N_PHI; ++p) {
        outfile << U_1d[p];
        if (p < N_PHI - 1) outfile << " ";
    }
    
    outfile << "\n";
    outfile.close();
    
    double sum = 0.0, min_val = U_1d[0], max_val = U_1d[0];
    for (int p = 0; p < N_PHI; ++p) {
        sum += U_1d[p];
        if (U_1d[p] < min_val) min_val = U_1d[p];
        if (U_1d[p] > max_val) max_val = U_1d[p];
    }
    double mean = sum / N_PHI;
    
    std::cout << "✓ Saved 1D IC to: " << output_file << "\n";
    std::cout << "  Grid: " << N_PHI << " points\n";
    std::cout << "  Location: Outer edge (r=" << target_rho << "/" << N_RHO 
              << ") at top (z=" << target_z << "/" << NZ << ")\n";
    std::cout << "  Statistics: Min=" << min_val << ", Max=" << max_val << ", Mean=" << mean << "\n";
}


void generateAll() {
    std::cout << "=== Generating Complete IC Set ===\n";
    std::cout << "Using unified parameters from constants.hpp:\n";
    std::cout << "  N_RHO = " << N_RHO << "\n";
    std::cout << "  N_PHI = " << N_PHI << "\n";
    std::cout << "  NZ = " << NZ << "\n";
    std::cout << "  R = " << R << "\n";
    std::cout << "  H = " << H << "\n\n";
    
    // Generate 3D master IC
    std::cout << "Step 1: Generate 3D master IC\n";
    generate3DInitialConditions("ic/master_ic.dat");
    std::cout << "\n";
    
    // Extract 2D polar
    std::cout << "Step 2: Extract 2D polar IC (from top disk)\n";
    extractPolar2D("ic/master_ic.dat", "ic/ic_polar.dat");
    std::cout << "\n";
    
    // Extract 2D cylindrical
    std::cout << "Step 3: Extract 2D cylindrical IC (from outer surface)\n";
    extractCylindrical2D("ic/master_ic.dat", "ic/ic_cyl.dat");
    std::cout << "\n";
    
    // Extract 1D
    std::cout << "Step 4: Extract 1D IC (from outer edge at top)\n";
    extract1D("ic/master_ic.dat", "ic/ic_1d.dat");
    std::cout << "\n";
    
    std::cout << "=== Complete IC Set Generated ===\n";
    std::cout << "All ICs extracted from same 3D master!\n\n";
    std::cout << "Files created in ic/ directory:\n";
    std::cout << "  - master_ic.dat (3D master)\n";
    std::cout << "  - ic_polar.dat (2D polar, from z=H top disk)\n";
    std::cout << "  - ic_cyl.dat (2D cylindrical, from r=R outer surface)\n";
    std::cout << "  - ic_1d.dat (1D, from r=R, z=H outer edge at top)\n\n";
    std::cout << "Location consistency:\n";
    std::cout << "  - Polar edge (r=R) matches 1D\n";
    std::cout << "  - Cylindrical top (z=H) matches 1D\n";
    std::cout << "  - All three share the same values at r=R, z=H\n\n";
    std::cout << "You can now run your simulations with consistent IC!\n";
}


void printUsage() {
    std::cout << "Usage:\n";
    std::cout << "  Complete workflow: ./ic_gen all\n";
    std::cout << "    Generates 3D master, then extracts all 2D and 1D ICs\n";
    std::cout << "\n";
    std::cout << "  Generate 3D: ./ic_gen generate3d <output.dat>\n";
    std::cout << "  Extract polar: ./ic_gen extract_polar <input_3d.dat> <output_2d.dat>\n";
    std::cout << "  Extract cylindrical: ./ic_gen extract_cyl <input_3d.dat> <output_2d.dat>\n";
    std::cout << "  Extract 1D: ./ic_gen extract_1d <input_3d.dat> <output_1d.dat>\n";
    std::cout << "\n";
    std::cout << "Examples:\n";
    std::cout << "  ./ic_gen all\n";
    std::cout << "  ./ic_gen generate3d ic/my_3d_ic.dat\n";
    std::cout << "  ./ic_gen extract_1d ic/master_ic.dat ic/my_1d_ic.dat\n";
    std::cout << "\n";
    std::cout << "Note: All ICs are extracted from the same 3D master for consistency!\n";
    std::cout << "      1D comes from outer edge at top (r=R, z=H) - interface location\n";
}


int main(int argc, char* argv[]) {
    std::cout << "=== Initial Conditions Generator ===\n";
    std::cout << "Supports: 1D, 2D (polar, cylindrical), 3D\n";
    std::cout << "All ICs extracted from same 3D master for consistency\n";
    
    if (argc < 2) {
        printUsage();
        return 1;
    }
    
    string command = argv[1];
    
    if (command == "all") {
        generateAll();
    }
    else if (command == "generate3d") {
        if (argc < 3) {
            std::cerr << "ERROR: Output filename required\n";
            printUsage();
            return 1;
        }
        generate3DInitialConditions(argv[2]);
    }
    else if (command == "extract_polar") {
        if (argc < 4) {
            std::cerr << "ERROR: Input and output filenames required\n";
            printUsage();
            return 1;
        }
        extractPolar2D(argv[2], argv[3]);
    }
    else if (command == "extract_cyl") {
        if (argc < 4) {
            std::cerr << "ERROR: Input and output filenames required\n";
            printUsage();
            return 1;
        }
        extractCylindrical2D(argv[2], argv[3]);
    }
    else if (command == "extract_1d") {
        if (argc < 4) {
            std::cerr << "ERROR: Input and output filenames required\n";
            printUsage();
            return 1;
        }
        extract1D(argv[2], argv[3]);
    }
    else {
        std::cerr << "ERROR: Unknown command: " << command << "\n";
        printUsage();
        return 1;
    }
    
    std::cout << "\nDone!\n";
    return 0;
}