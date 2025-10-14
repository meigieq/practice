
# 인덱스 구조

# 키워드 인덱스
def create_keyword_index():
    index_keyword_config = {
        "settings": {
            "index": { 
                "number_of_shards": 2,
                "number_of_replicas": 1
            },
            "analysis": {
                "tokenizer": {
                    "my_nori_tokenizer": {
                        "type": "nori_tokenizer",
                        "decompound_mode": "discard",
                    }
                },
                "filter": {
                    "nori_pos_filter_useful_nouns": {
                    "type": "nori_part_of_speech",
                    "stoptags": [ 
                            "JKS","JKC","JKO","JKB","JKG","JX","JC",
                            "EP","EF","EC","ETN","ETM",
                            "XPN","XSN","XSV","XSA",
                            "SF","SP","SSO","SSC","SY","UNA","UNKNOWN"]  
                    },
                    "remove_special_chars": {
                        "type": "pattern_replace",
                        "pattern": "[?!@#$^&*]",
                        "replacement": ""
                    },
                    "en_stop": {
                        "type": "stop",
                        "stopwords": "_english_"
                    },
                    "my_synonym_filter": {
                        "type": "synonym_graph",
                        "synonyms_path": "analysis/custom_synonym.txt",
                        "updateable": True
                    },
                    "wdg": {
                        "type": "word_delimiter_graph",
                        "split_on_case_change": True,
                        "split_on_numerics": True,
                        "generate_word_parts": True,
                        "generate_number_parts": True,
                        "preserve_original": True,
                        "catenate_words": False,
                        "catenate_numbers": False
                    },
                },
                "analyzer": {
                    "mix_analyzer": {
                        "type": "custom",
                        "tokenizer": "my_nori_tokenizer",
                        "filter": ["wdg", "lowercase", "nori_pos_filter_useful_nouns", "en_stop", "remove_special_chars"]
                    },
                    "search_analyzer": {
                        "type": "custom",
                        "tokenizer": "my_nori_tokenizer",
                        "filter": ["my_synonym_filter", "wdg", "lowercase", "remove_special_chars", "en_stop", "nori_pos_filter_useful_nouns"]
                    }
                },
            },
        },
        "mappings": {
            "dynamic": False,
            "properties": {
                "category_id":   { "type": "keyword" },
                "category_name": { "type": "keyword" },
                "cat_join": {
                    "type": "join",
                    "relations": { "category": "doc" }},
                "doc_id": {"type": "keyword", "ignore_above": 512},
                "doc_title": {
                    "type": "keyword",
                    "ignore_above": 512,
                    "fields": {
                        "ko": { "type": "text", "analyzer": "mix_analyzer", "search_analyzer": "search_analyzer" }
                    }
                },
                "doc_type": { "type": "keyword" },
                "page_number": { "type": "integer" },
                "chunk_id": { "type": "keyword", "ignore_above": 512 },
                "content": { "type": "text", "analyzer": "mix_analyzer", "search_analyzer": "search_analyzer" },
                "file_url":  { "type": "keyword", "ignore_above": 2048 },

                "image_refs": {
                    "type": "nested",
                    "properties": {
                        "url":        { "type": "keyword", "ignore_above": 2048 },
                        "local_name": { "type": "keyword", "ignore_above": 512 },
                        "page":       { "type": "integer" },
                        "index":        { "type": "integer" },
                    }
                },
                "image_thumb": { "type": "binary", "store": True },
                "image_thumb_mime": {"type": "keyword", "ignore_above": 64},

                "metadata": {
                    "type":"object",
                    "dynamic": True,
                    "properties": {
                        "doc_id":       { "type": "keyword", "ignore_above": 512 },
                        "doc_title":      { "type": "keyword", "ignore_above": 512 },
                        "doc_type":       { "type": "keyword" },
                        "page_number":    { "type": "integer" },
                        "file_url":       { "type": "keyword", "ignore_above": 2048 },
                        "image":          { "type": "text", "index": False },
                        "md_content": { "type": "text", "analyzer": "mix_analyzer", "search_analyzer": "search_analyzer" }, 
                    }
                }
            }
        }
    }
    return index_keyword_config


# 벡터 인덱스
def create_vector_index():
    index_vector_config = {
        "settings": {
            "index": {
                "knn": True,
                "number_of_shards": 2,
                "number_of_replicas": 1,
                "knn.algo_param.ef_search": 100,
            },
            "analysis": {
                    "tokenizer": {
                    "my_nori_tokenizer": {
                        "type": "nori_tokenizer",
                        "decompound_mode": "mixed",
                    }
                },
                "filter": {
                    "nori_pos_filter_useful_nouns": {
                        "type": "nori_part_of_speech",
                        "stoptags": [
                            "JKS","JKC","JKO","JKB","JKG","JX","JC",
                            "EP","EF","EC","ETN","ETM",
                            "XPN","XSN","XSV","XSA",
                            "SF","SP","SSO","SSC","SY","UNA","UNKNOWN"
                        ]
                    },
                    "remove_special_chars": {
                        "type": "pattern_replace",
                        "pattern": "[?!@#$^&*]",
                        "replacement": ""
                    },
                    "en_stop": {
                        "type": "stop",
                        "stopwords": "_english_"
                   },
                    "wdg": {
                        "type": "word_delimiter_graph",
                        "split_on_case_change": True,
                        "split_on_numerics": True,
                        "generate_word_parts": True,
                        "generate_number_parts": True,
                        "preserve_original": True,
                        "catenate_words": False,
                        "catenate_numbers": False
                    },
                },
                "analyzer": {
                    "mix_analyzer": {
                        "type": "custom",
                        "tokenizer": "my_nori_tokenizer",
                        "filter": ["wdg", "lowercase","remove_special_chars","en_stop","nori_pos_filter_useful_nouns"]
                    },
                    "search_analyzer": {  
                        "type": "custom",
                        "tokenizer": "my_nori_tokenizer",
                        "filter": ["wdg", "lowercase","remove_special_chars","en_stop","nori_pos_filter_useful_nouns"]
                    }
                }
            }
        },
        "mappings": {
            "dynamic": False,
            "properties": {
                "category_id":   { "type": "keyword" },
                "category_name": { "type": "keyword" },
                "cat_join": {
                    "type": "join",
                    "relations": { "category": "doc" }},
                "doc_id": {"type": "keyword", "ignore_above": 512},
                "doc_title": {
                    "type": "keyword",
                    "ignore_above": 512,
                    "fields": {
                        "ko": { "type": "text", "analyzer": "mix_analyzer", "search_analyzer": "search_analyzer" }
                    }
                },
                "doc_type": { "type": "keyword" },
                "page_number": { "type": "integer" },
                "chunk_id": { "type": "keyword", "ignore_above": 512 },
                "content": { "type": "text", "analyzer": "mix_analyzer", "search_analyzer": "search_analyzer" },
                "file_url":  { "type": "keyword", "ignore_above": 2048 },

                "image_refs": {
                    "type": "nested",
                    "properties": {
                        "url":        { "type": "keyword", "ignore_above": 2048 },
                        "local_name": { "type": "keyword", "ignore_above": 512 },
                        "page":       { "type": "integer" },
                        "index":        { "type": "integer" },
                    }
                },
                "image_thumb": { "type": "binary", "store": True },
                "image_thumb_mime": {"type": "keyword", "ignore_above": 64},

                "vector_field": {
                    "type": "knn_vector",
                    "dimension": 1024,      
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "faiss",
                        "parameters": {
                            "ef_construction": 128,
                            "m": 24
                        }
                    }
                },

                "metadata": {
                    "type": "object",
                    "dynamic": True,
                    "properties": {
                        "doc_id":       { "type": "keyword", "ignore_above": 512 },
                        "doc_title":      { "type": "keyword", "ignore_above": 512 },
                        "doc_type":       { "type": "keyword" },
                        "page_number":    { "type": "integer" }, 
                        "file_url":       { "type": "keyword", "ignore_above": 2048 },
                        "image":          { "type": "text", "index": False },
                        "md_content": { "type": "text", "analyzer": "mix_analyzer", "search_analyzer": "search_analyzer" }, 
                    }
                }
            },
        }
    }
    return index_vector_config