#pragma once

#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <cmath>
#include <numeric>
#include <iostream>
#include "indexer.hpp"

namespace apex {

struct LinkEdge {
    int source_id;
    int target_id;
};

class PageRankEngine {
public:
    PageRankEngine(double damping = 0.85, int max_iterations = 100, double tol = 1e-6)
        : damping(damping), max_iterations(max_iterations), tolerance(tol) {}

    void add_link(int source, int target) {
        if (source != target) {
            edges.push_back({source, target});
        }
    }

    void compute(InvertedIndex& index) {
        const auto& docs = index.get_all_documents();
        int N = static_cast<int>(docs.size());
        if (N == 0) return;

        // Build doc id list and map
        std::vector<int> doc_ids;
        std::unordered_set<int> doc_set;
        for (const auto& kv : docs) {
            doc_ids.push_back(kv.first);
            doc_set.insert(kv.first);
        }

        std::unordered_map<int, std::vector<int>> out_links;
        std::unordered_map<int, std::vector<int>> in_links;

        for (const auto& edge : edges) {
            if (doc_set.count(edge.source_id) && doc_set.count(edge.target_id)) {
                out_links[edge.source_id].push_back(edge.target_id);
                in_links[edge.target_id].push_back(edge.source_id);
            }
        }

        // Initialize uniform distribution PR_0 = 1 / N
        std::unordered_map<int, double> ranks;
        for (int id : doc_ids) {
            ranks[id] = 1.0 / N;
        }

        // Power Iteration Loop
        for (int iter = 0; iter < max_iterations; ++iter) {
            std::unordered_map<int, double> new_ranks;

            // Compute rank contribution of dangling nodes (nodes with 0 outbound links)
            double dangling_sum = 0.0;
            for (int id : doc_ids) {
                if (out_links[id].empty()) {
                    dangling_sum += ranks[id];
                }
            }

            double diff = 0.0;
            for (int id : doc_ids) {
                double rank = (1.0 - damping) / N + (damping * dangling_sum / N);

                for (int in_id : in_links[id]) {
                    size_t out_degree = out_links[in_id].size();
                    if (out_degree > 0) {
                        rank += damping * (ranks[in_id] / static_cast<double>(out_degree));
                    }
                }

                diff += std::abs(rank - ranks[id]);
                new_ranks[id] = rank;
            }

            ranks = new_ranks;
            if (diff < tolerance) {
                break;
            }
        }

        // Normalize so average rank = 1.0
        double sum = 0.0;
        for (int id : doc_ids) sum += ranks[id];
        double avg = (N > 0) ? (sum / N) : 1.0;

        for (int id : doc_ids) {
            double normalized_score = (avg > 0) ? (ranks[id] / avg) : 1.0;
            index.set_pagerank(id, normalized_score);
        }
    }

private:
    double damping;
    int max_iterations;
    double tolerance;
    std::vector<LinkEdge> edges;
};

} // namespace apex

