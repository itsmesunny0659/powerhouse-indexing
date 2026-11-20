#pragma once

#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <sstream>
#include "indexer.hpp"

namespace apex {

struct SearchHit {
    int doc_id;
    std::string url;
    std::string title;
    double bm25_score;
    double pagerank_score;
    double final_score;
    int word_count;
};

class BM25Ranker {
public:
    BM25Ranker(double k1 = 1.5, double b = 0.75, double pr_weight = 0.35)
        : k1(k1), b(b), pr_weight(pr_weight) {}

    std::vector<SearchHit> score(const InvertedIndex& index, const std::string& query, int limit = 20) const {
        std::vector<std::string> query_terms = tokenize_query(query);
        if (query_terms.empty()) return {};

        size_t N = index.get_total_documents();
        if (N == 0) return {};

        double avgdl = index.get_avg_doc_length();

        // Accumulate document BM25 scores: doc_id -> score
        std::unordered_map<int, double> doc_scores;

        for (const std::string& term : query_terms) {
            const auto* postings = index.get_postings(term);
            if (!postings) continue;

            int n_q = index.get_doc_freq(term);
            
            // Robertson-Spärck Jones IDF formula
            double idf = std::log((N - n_q + 0.5) / (n_q + 0.5) + 1.0);
            if (idf < 0.0) idf = 0.001;

            for (const auto& post : *postings) {
                const Document* doc = index.get_document(post.doc_id);
                if (!doc) continue;

                int tf = post.term_frequency;
                int doc_len = doc->word_count;

                // Okapi BM25 TF component
                double denom = tf + k1 * (1.0 - b + b * (static_cast<double>(doc_len) / avgdl));
                double tf_component = (tf * (k1 + 1.0)) / (denom > 0 ? denom : 1.0);
                double term_score = idf * tf_component;

                // Title match signal boost (2.5x)
                std::string title_lower = to_lower(doc->title);
                if (title_lower.find(term) != std::string::npos) {
                    term_score *= 2.5;
                }

                doc_scores[post.doc_id] += term_score;
            }
        }

        // Rank documents with PageRank Authority
        std::vector<SearchHit> hits;
        for (const auto& kv : doc_scores) {
            int doc_id = kv.first;
            double bm25 = kv.second;

            const Document* doc = index.get_document(doc_id);
            if (!doc) continue;

            double pr = doc->pagerank;
            double pr_multiplier = 1.0 + pr_weight * std::log(1.0 + pr);
            double final_score = bm25 * pr_multiplier;

            hits.push_back({
                doc_id,
                doc->url,
                doc->title,
                round_score(bm25),
                round_score(pr),
                round_score(final_score),
                doc->word_count
            });
        }

        // Sort descending by final score
        std::sort(hits.begin(), hits.end(), [](const SearchHit& a, const SearchHit& b) {
            return a.final_score > b.final_score;
        });

        if (hits.size() > static_cast<size_t>(limit)) {
            hits.resize(limit);
        }

        return hits;
    }

private:
    double k1;
    double b;
    double pr_weight;

    static double round_score(double val) {
        return std::round(val * 10000.0) / 10000.0;
    }

    static std::string to_lower(std::string str) {
        std::transform(str.begin(), str.end(), str.begin(), ::tolower);
        return str;
    }

    static std::vector<std::string> tokenize_query(const std::string& query) {
        std::vector<std::string> tokens;
        static const std::regex word_regex(R"([a-zA-Z0-9_\-\']{2,})");
        auto begin = std::sregex_iterator(query.begin(), query.end(), word_regex);
        auto end = std::sregex_iterator();

        for (auto i = begin; i != end; ++i) {
            std::string t = i->str();
            std::transform(t.begin(), t.end(), t.begin(), ::tolower);
            tokens.push_back(t);
        }
        return tokens;
    }
};

} // namespace apex

