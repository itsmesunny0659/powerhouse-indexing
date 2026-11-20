#include <iostream>
#include <chrono>
#include <iomanip>
#include "../include/robots.hpp"
#include "../include/indexer.hpp"
#include "../include/pagerank.hpp"
#include "../include/bm25.hpp"
#include "../include/google_handshake.hpp"

int main(int argc, char* argv[]) {
    std::cout << "============================================================\n";
    std::cout << "  🚀 APEXSEARCH C++ CORE ENGINE (Google-Grade Implementation)\n";
    std::cout << "============================================================\n";

    // 1. Robots.txt Engine Test
    std::cout << "\n[1] Testing C++ Robots.txt Validator...\n";
    apex::RobotsParser robots;
    std::string sample_robots = 
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Disallow: /private/\n"
        "Allow: /public/\n"
        "Crawl-delay: 1.5\n";

    robots.parse(sample_robots, "ApexBot");
    std::cout << " - Is '/public/docs' allowed? " << (robots.is_allowed("/public/docs") ? "YES (ALLOW)" : "NO (BLOCK)") << "\n";
    std::cout << " - Is '/admin/login' allowed? " << (robots.is_allowed("/admin/login") ? "YES (ALLOW)" : "NO (BLOCK)") << "\n";
    std::cout << " - Discovered Crawl-Delay: " << robots.get_crawl_delay() << "s\n";

    // 2. High-Performance Inverted Index Construction
    std::cout << "\n[2] Building C++ Positional Inverted Index...\n";
    apex::InvertedIndex index;

    auto t1 = std::chrono::high_resolution_clock::now();

    index.add_document(1, "https://engine.internal/doc1", "Google Search Engine Architecture",
        "The Google search engine relies on distributed web crawlers, inverted indexing, and the PageRank algorithm.");
    
    index.add_document(2, "https://engine.internal/doc2", "Advanced Machine Learning with Transformers",
        "Deep learning and transformer neural networks power modern semantic search, natural language understanding, and embeddings.");

    index.add_document(3, "https://engine.internal/doc3", "High Performance C++ Systems Programming",
        "C++ provides zero-cost abstractions, multi-threaded concurrency, low latency, and deterministic memory management.");

    index.add_document(4, "https://engine.internal/doc4", "Distributed Web Crawling and Sockets",
        "Asynchronous socket I/O and politeness rate limiting allow crawlers to fetch millions of web pages per second.");

    auto t2 = std::chrono::high_resolution_clock::now();
    double index_ms = std::chrono::duration<double, std::milli>(t2 - t1).count();

    std::cout << " - Indexed " << index.get_total_documents() << " documents in " << index_ms << " ms\n";
    std::cout << " - Unique vocabulary size: " << index.get_vocabulary_size() << " terms\n";
    std::cout << " - Average document length: " << index.get_avg_doc_length() << " tokens\n";

    // 3. PageRank Power-Iteration Algorithm
    std::cout << "\n[3] Computing Google PageRank Authority...\n";
    apex::PageRankEngine pr_engine(0.85, 100, 1e-6);
    // Link structure: doc1 -> doc2, doc3 -> doc2, doc4 -> doc2 (doc2 has massive inbound authority!)
    pr_engine.add_link(1, 2);
    pr_engine.add_link(3, 2);
    pr_engine.add_link(4, 2);
    pr_engine.add_link(2, 1);

    auto pr_start = std::chrono::high_resolution_clock::now();
    pr_engine.compute(index);
    auto pr_end = std::chrono::high_resolution_clock::now();
    double pr_ms = std::chrono::duration<double, std::milli>(pr_end - pr_start).count();

    std::cout << " - PageRank converged in " << pr_ms << " ms\n";
    for (const auto& kv : index.get_all_documents()) {
        std::cout << "   * Doc #" << kv.first << " (" << kv.second.title.substr(0, 30) << "...): PageRank = " 
                  << std::fixed << std::setprecision(4) << kv.second.pagerank << "\n";
    }

    // 4. Okapi BM25 Ranking Query
    std::cout << "\n[4] Executing BM25 + PageRank Query: 'search engine c++'...\n";
    apex::BM25Ranker ranker;

    auto q_start = std::chrono::high_resolution_clock::now();
    auto hits = ranker.score(index, "search engine c++", 5);
    auto q_end = std::chrono::high_resolution_clock::now();
    double q_us = std::chrono::duration<double, std::micro>(q_end - q_start).count();

    std::cout << " - Query executed in " << q_us << " microseconds (µs)!\n";
    std::cout << " - Ranked Hits:\n";

    for (size_t i = 0; i < hits.size(); ++i) {
        const auto& hit = hits[i];
        std::cout << "   #" << (i + 1) << " [Score: " << hit.final_score 
                  << " | BM25: " << hit.bm25_score 
                  << " | PR: " << hit.pagerank_score << "] " 
                  << hit.title << " (" << hit.url << ")\n";
    }

    // 5. Google High-Priority Handshake & Token Rotator Engine (100k URLs/day)
    std::cout << "\n[5] Testing Google High-Priority Handshake Gateway (100,000 URLs/day Architecture)...\n";
    apex::GoogleHandshakeEngine handshake_engine;
    std::vector<apex::HandshakeRequest> sample_batch = {
        {"https://partner-portal.org/breaking-news", "URL_UPDATED", "HIGH_PRIORITY_URGENT"},
        {"https://cloud-enterprise.net/docs/api-v3", "URL_UPDATED", "HIGH_PRIORITY_URGENT"},
        {"https://fintech-daily.com/market-update", "URL_UPDATED", "HIGH_PRIORITY_URGENT"}
    };

    auto hs_t0 = std::chrono::high_resolution_clock::now();
    auto receipts = handshake_engine.process_batch(sample_batch);
    auto hs_t1 = std::chrono::high_resolution_clock::now();
    double hs_us = std::chrono::duration<double, std::micro>(hs_t1 - hs_t0).count();

    for (const auto& r : receipts) {
        std::cout << " - [Handshake " << r.http_status << " OK] " << r.url 
                  << " | Token: " << r.token_id 
                  << " | Sig: " << r.whitelist_signature 
                  << " | Latency: " << r.latency_us << " µs\n";
    }
    std::cout << " - Batch of " << receipts.size() << " URLs processed in " << hs_us << " µs (Handshake Mode Confirmed)\n";

    std::cout << "\n============================================================\n";
    std::cout << "  C++ Core Engine Verification Complete.\n";
    std::cout << "============================================================\n";

    return 0;
}

