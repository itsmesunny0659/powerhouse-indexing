#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <regex>
#include <cmath>
#include <algorithm>
#include <iostream>

namespace apex {

struct Posting {
    int doc_id;
    int term_frequency;
    std::vector<int> positions;
};

struct Document {
    int id;
    std::string url;
    std::string title;
    std::string text;
    int word_count{0};
    double pagerank{1.0};
};

class InvertedIndex {
public:
    InvertedIndex() {
        // Core stop words
        stopwords = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", 
            "any", "are", "as", "at", "be", "because", "been", "before", "being", "below", 
            "between", "both", "but", "by", "could", "did", "do", "does", "doing", "down", 
            "during", "each", "few", "for", "from", "further", "had", "has", "have", "he", 
            "her", "here", "hers", "him", "his", "how", "i", "if", "in", "into", "is", 
            "it", "its", "just", "me", "more", "most", "my", "no", "nor", "not", "of", 
            "off", "on", "once", "only", "or", "other", "our", "out", "over", "own", 
            "same", "she", "should", "so", "some", "such", "than", "that", "the", "their", 
            "them", "then", "there", "these", "they", "this", "those", "through", "to", 
            "too", "under", "until", "up", "very", "was", "we", "were", "what", "when", 
            "where", "which", "while", "who", "whom", "why", "with", "would", "you", "your"
        };
    }

    std::vector<std::pair<std::string, int>> tokenize_with_positions(const std::string& text) const {
        std::vector<std::pair<std::string, int>> tokens;
        static const std::regex word_regex(R"([a-zA-Z0-9_\-\']{2,})");
        auto words_begin = std::sregex_iterator(text.begin(), text.end(), word_regex);
        auto words_end = std::sregex_iterator();

        for (std::sregex_iterator i = words_begin; i != words_end; ++i) {
            std::smatch match = *i;
            std::string match_str = match.str();
            std::transform(match_str.begin(), match_str.end(), match_str.begin(), ::tolower);

            if (stopwords.find(match_str) == stopwords.end()) {
                tokens.push_back({match_str, static_cast<int>(match.position())});
            }
        }
        return tokens;
    }

    void add_document(int id, const std::string& url, const std::string& title, const std::string& text) {
        Document doc;
        doc.id = id;
        doc.url = url;
        doc.title = title;
        doc.text = text;

        std::string full_text = title + " " + title + " " + text;
        auto tokens = tokenize_with_positions(full_text);
        doc.word_count = static_cast<int>(tokens.size());

        total_word_count += doc.word_count;
        documents[id] = doc;

        // Group tokens into term frequency and positions
        std::unordered_map<std::string, std::pair<int, std::vector<int>>> tf_map;
        for (const auto& token_pos : tokens) {
            const std::string& term = token_pos.first;
            int pos = token_pos.second;
            tf_map[term].first++;
            tf_map[term].second.push_back(pos);
        }

        // Update postings and document frequency
        for (const auto& entry : tf_map) {
            const std::string& term = entry.first;
            int tf = entry.second.first;
            const auto& positions = entry.second.second;

            Posting posting;
            posting.doc_id = id;
            posting.term_frequency = tf;
            posting.positions = positions;

            index[term].push_back(posting);
            doc_frequencies[term]++;
        }
    }

    const std::vector<Posting>* get_postings(const std::string& term) const {
        auto it = index.find(term);
        if (it != index.end()) {
            return &it->second;
        }
        return nullptr;
    }

    int get_doc_freq(const std::string& term) const {
        auto it = doc_frequencies.find(term);
        if (it != doc_frequencies.end()) {
            return it->second;
        }
        return 0;
    }

    const Document* get_document(int id) const {
        auto it = documents.find(id);
        if (it != documents.end()) {
            return &it->second;
        }
        return nullptr;
    }

    void set_pagerank(int doc_id, double score) {
        auto it = documents.find(doc_id);
        if (it != documents.end()) {
            it->second.pagerank = score;
        }
    }

    size_t get_total_documents() const { return documents.size(); }
    size_t get_vocabulary_size() const { return index.size(); }
    double get_avg_doc_length() const {
        return documents.empty() ? 100.0 : static_cast<double>(total_word_count) / documents.size();
    }

    const std::unordered_map<int, Document>& get_all_documents() const {
        return documents;
    }

private:
    std::unordered_set<std::string> stopwords;
    std::unordered_map<int, Document> documents;
    std::unordered_map<std::string, std::vector<Posting>> index;
    std::unordered_map<std::string, int> doc_frequencies;
    size_t total_word_count{0};
};

} // namespace apex

