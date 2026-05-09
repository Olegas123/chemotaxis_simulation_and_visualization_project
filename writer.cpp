// writer.cpp
#include "writer.hpp"
#include <ctime>
#include <iomanip>
#include <iostream>

Writer::Writer(const std::string& runName,
               const std::map<std::string, double>& params,
               const std::string& resultsDir)
{
    // Generate filename with full path (assumes resultsDir exists)
    fullPath = makeFilename(runName, resultsDir);
    file.open(fullPath);

    if (!file.is_open()) {
        std::cerr << "ERROR: cannot open snapshot file: " << fullPath << "\n";
        std::cerr << "Make sure the '" << resultsDir << "' directory exists!\n";
        return;
    }

    fileOpen = true;
    file << std::setprecision(15);

    writeHeader(params);
    
    std::cout << "Output file: " << fullPath << "\n";
}

Writer::~Writer() {
    if (fileOpen) {
        file.close();
        std::cout << "Closed output file: " << fullPath << "\n";
    }
}

std::string Writer::makeFilename(const std::string& runName, 
                                 const std::string& resultsDir)
{
    // Timestamp
    std::time_t now = std::time(nullptr);
    std::tm* ptm = std::localtime(&now);

    char timestamp[64];
    std::strftime(timestamp, sizeof(timestamp), "%Y%m%d_%H%M%S", ptm);

    // Build full path: results/runName_timestamp.dat
    return resultsDir + "/" + runName + "_" + timestamp + ".dat";
}

void Writer::writeHeader(const std::map<std::string, double>& params)
{
    file << "# MODEL SNAPSHOT FILE\n";
    file << "# Generated: " << fullPath << "\n";
    for (auto& kv : params) {
        file << "# " << kv.first << " = " << kv.second << "\n";
    }
    file << "#\n";
    file << "# Each snapshot begins with:\n";
    file << "# SNAPSHOT t=<time>\n";
    file << "# Values: just values (no coordinates)\n";
    file << "#\n";
}

void Writer::ensureOpen() {
    if (!fileOpen) {
        std::cerr << "Writer error: file not open.\n";
    }
}

//
// ----------- SNAPSHOT WRITERS -----------
//

void Writer::saveSnapshot2Dside(double t, const std::vector<std::vector<double>>& u)
{
    ensureOpen();
    if (!fileOpen) return;

    int NPhi = u.size();
    int NZ = u[0].size();

    file << "\nSNAPSHOT t=" << t << "\n";

    // Transpose: write z-levels as rows, phi values as columns
    // This matches the format of polar model and 3D model
    for (int z = 0; z < NZ; z++) {
        for (int phi = 0; phi < NPhi; phi++) {
            file << u[phi][z] << " ";
        }
        file << "\n";
    }

    file.flush();
}

void Writer::saveSnapshot2Dtop(double t, const std::vector<std::vector<double>>& u)
{
    ensureOpen();
    if (!fileOpen) return;

    int NR = u.size();
    int NPhi = u[0].size();

    file << "\nSNAPSHOT t=" << t << "\n";

    for (int r = 0; r < NR; r++) {
        for (int p = 0; p < NPhi; p++) {
            file << u[r][p] <<  " ";
        }
        file << "\n";
    }

    file.flush();
}

void Writer::saveSnapshot3D(double t, const std::vector<std::vector<std::vector<double>>>& u)
{
    ensureOpen();
    if (!fileOpen) return;

    // Get dimensions from the array
    int NRho = u.size();
    int NPhi = u[0].size();
    int NZ = u[0][0].size();

    file << "\nSNAPSHOT t=" << t << "\n";

    for (int rho = 0; rho < NRho; rho++) {
        for (int z = 0; z < NZ; z++) {
            for (int phi = 0; phi < NPhi; phi++) {
                file << u[rho][phi][z] << " ";
            }
            file << "\n";
        }
    }

    file.flush();
}