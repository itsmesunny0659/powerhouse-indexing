#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <algorithm>
#include <sstream>

namespace apex {

struct Rule {
    std::string path_prefix;
    bool allowed;
};

class RobotsParser {
public:
    RobotsParser() = default;

    void parse(const std::string& robots_content, const std::string& target_ua = "ApexBot") {
        rules.clear();
        crawl_delay = 0.0;
        
        std::istringstream stream(robots_content);
        std::string line;
        bool applies_to_us = false;

        while (std::getline(stream, line)) {
            // Remove comments and whitespace
            size_t comment_pos = line.find('#');
            if (comment_pos != std::string::npos) {
                line = line.substr(0, comment_pos);
            }
            line = trim(line);
            if (line.empty()) continue;

            size_t colon_pos = line.find(':');
            if (colon_pos == std::string::npos) continue;

            std::string key = to_lower(trim(line.substr(0, colon_pos)));
            std::string value = trim(line.substr(colon_pos + 1));

            if (key == "user-agent") {
                std::string ua = to_lower(value);
                applies_to_us = (ua == "*" || ua == to_lower(target_ua) || ua == "googlebot");
            } else if (applies_to_us) {
                if (key == "disallow") {
                    if (value.empty()) {
                        // Disallow: means allow all
                        rules.push_back({"/", true});
                    } else {
                        rules.push_back({value, false});
                    }
                } else if (key == "allow") {
                    rules.push_back({value, true});
                } else if (key == "crawl-delay") {
                    try {
                        crawl_delay = std::stod(value);
                    } catch (...) {
                        crawl_delay = 0.0;
                    }
                }
            }
        }
    }

    bool is_allowed(const std::string& path) const {
        if (rules.empty()) return true;

        // Longest prefix match rule (Google Standard)
        size_t longest_match = 0;
        bool allowed = true;

        for (const auto& rule : rules) {
            if (path.rfind(rule.path_prefix, 0) == 0) { // starts with
                if (rule.path_prefix.length() >= longest_match) {
                    longest_match = rule.path_prefix.length();
                    allowed = rule.allowed;
                }
            }
        }
        return allowed;
    }

    double get_crawl_delay() const { return crawl_delay; }

private:
    std::vector<Rule> rules;
    double crawl_delay{0.0};

    static std::string trim(const std::string& str) {
        size_t first = str.find_first_not_of(" \t\r\n");
        if (first == std::string::npos) return "";
        size_t last = str.find_last_not_of(" \t\r\n");
        return str.substr(first, (last - first + 1));
    }

    static std::string to_lower(std::string str) {
        std::transform(str.begin(), str.end(), str.begin(), ::tolower);
        return str;
    }
};

} // namespace apex

