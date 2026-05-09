// writer.hpp
#pragma once
#include <vector>
#include <string>
#include <fstream>
#include <map>

class Writer {
public:
    Writer(const std::string& runName,
           const std::map<std::string, double>& params,
           const std::string& resultsDir = "results");

    // Snapshots (save u only)
    void saveSnapshot2Dside(double t, const std::vector<std::vector<double>>& u);
    void saveSnapshot2Dtop(double t, const std::vector<std::vector<double>>& u);
    void saveSnapshot3D(double t, const std::vector<std::vector<std::vector<double>>>& u);

    // Close file on destruction
    ~Writer();

private:
    std::ofstream file;
    bool fileOpen = false;
    std::string fullPath;  // Store full path for later reference

    std::string makeFilename(const std::string& runName, const std::string& resultsDir);
    void writeHeader(const std::map<std::string, double>& params);
    void ensureOpen();
};