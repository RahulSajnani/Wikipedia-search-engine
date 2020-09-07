import xml.etree.ElementTree as etree
import sys
import config
import re
import Stemmer
import os
import linecache
import heapq
import readline
from datetime import datetime
from operator import itemgetter
import time

'''
Author: Rahul Sajnani
'''
        
class Engine:
    '''
    Search engine class
    
    '''

    def __init__(self, index_path):
        super().__init__()

        assert os.path.exists(index_path), "Index path does not exist"
        self.index_path = index_path
        self.categories = sorted(["references", "body", "infobox", "title", "category", "links"])
        self.query_categories = {"c:": "category", "b:": "body", "t:": "title", "i:": "infobox", "r:": "references", "e:": "links"}
        self.tokens_dict = self.get_tokens()
        self.stemmer = Stemmer.Stemmer("english")
        self.titles_file = os.path.join(index_path, "titles.txt")
        self.file_pointers = self.get_index_pointers()
        self.relevance_weights = {"references": 0.1, "body": 0.5, "infobox": 1.5, "title": 3, "category": 1, "links": 0.1}
    
    def get_tokens(self):
        '''
        Reads the tokens file with line numbers
        '''
        tokens_dict = {}
        with open(os.path.join(self.index_path, "tokens.txt"), "r") as fp:
            for line in fp:
                words = line.split()
                if tokens_dict.get(words[0]) is None:
                    tokens_dict[words[0]] = []
                for i in range(1, len(words)):
                    tokens_dict[words[0]].append(words[i])

        return tokens_dict
    
    def get_index_pointers(self):
        '''
        Get file pointers for index files
        '''
        file_dict = {}
        for field in self.categories:
            for block in range(config.max_division):
                filename = "index_block_%d_%s.txt" % (block, str(field))
                file_dict[filename] = open(os.path.join(index_path, filename), "r")
        
        # print(file_)
        return file_dict


    def decode_line(self, line, category_weight):
        '''
        Decode line from the file containing posting's list
        '''
        
        line_dict = {}
        line = line.split()
        
        # line_dict["size"] = int(line[0])
        line_dict["postings_list"] = []
        
        for i in range(0, len(line), 2):
            line_dict["postings_list"].append((int(line[i]), category_weight * float(line[i + 1])))
        
        line_dict["size"] = len(line_dict["postings_list"])

        return line_dict


    def get_postings_list(self, query_dict):
        '''
        Get the index files
        '''
        
        postings_list = {}
        for category in query_dict:
            
            for token in query_dict[category]:
                # print(token)
                block = config.alphabet_file_mapping[token[0]]
                filename = "index_block_%d_%s.txt" % (block, str(category))
                fp = self.file_pointers[filename]
                found = False
                # If token in dictionary
                if (self.tokens_dict.get(token) is not None):
                    # If token is present in the respective category
                    if self.tokens_dict[token][self.categories.index(category)] != "n": 
                        # Get line :)
                        # print(self.tokens_dict[token][self.categories.index(category)])
                        seek_value = int(self.tokens_dict[token][self.categories.index(category)])
                        fp.seek(seek_value)
                        line = fp.readline()
                        postings_list_dict = self.decode_line(line, category_weight = self.relevance_weights[category])
                        found = True
                        if postings_list.get(category) is None:
                            postings_list[category] = {}
                        postings_list[category][token] = postings_list_dict

                if not found:
                    if postings_list.get(category) is None:
                        postings_list[category] = {}
                    postings_list[category][token] = {"size": 0, "postings_list": []}
        

        # print(postings_list)
        return postings_list


    def merge_postings_list(self, postings_list_1, postings_list_2):
        '''
        Merge two posting's list (intersection) 

        '''

        ptr_1 = 0
        ptr_2 = 0

        doc_id_list = []

        while ((ptr_1 < len(postings_list_1)) and (ptr_2 < len(postings_list_2))):
            
            if postings_list_1[ptr_1][0] > postings_list_2[ptr_2][0]:
                ptr_2 += 1

            elif postings_list_1[ptr_1][0] < postings_list_2[ptr_2][0]:
                ptr_1 += 1

            else:
                # Doc ids are same 
                avg_doc_count = (postings_list_1[ptr_1][1] + postings_list_2[ptr_2][1])
                doc_id_list.append((postings_list_1[ptr_1][0], avg_doc_count))

                ptr_1 += 1
                ptr_2 += 1

        return doc_id_list

    def find_top_k(self, search_doc_id, max_k):
        '''
        Find top k search results
        '''
        if max_k > 0:
            query_result = heapq.nlargest(max_k, search_doc_id, key=itemgetter(1))
        else:
            max_k = len(search_doc_id)
            query_result = heapq.nlargest(max_k, search_doc_id, key=itemgetter(1))

        return query_result

    def merge_postings_list_dict(self, posting_list_dict, max_k):
        '''
        Merges dictionary of postings list for a query
        '''

        # Doc ids of intersection of postings list
        search_doc_id = []
        postings_dict_size_heap = []
        all_postings_list = []
        # print(posting_list_dict)
        for category in posting_list_dict:
            for token in posting_list_dict[category]:
                postings_dict_size_heap.append((posting_list_dict[category][token]["size"], category, token))
                all_postings_list.append(posting_list_dict[category][token]["postings_list"])

        postings_dict_size_heap_join = list(postings_dict_size_heap)
        # print(postings_dict_size_heap)
        # If only one token
        if len(postings_dict_size_heap) == 1:
            return self.find_top_k(posting_list_dict[category][token]["postings_list"], max_k)

        heapq.heapify(postings_dict_size_heap)
        first_merge = True

        while postings_dict_size_heap:
            # print("merging")
            if len(postings_dict_size_heap) > 1 and first_merge:
                posting_tuple_1 = heapq.heappop(postings_dict_size_heap)
                posting_tuple_2 = heapq.heappop(postings_dict_size_heap)
                search_doc_id = self.merge_postings_list(posting_list_dict[posting_tuple_1[1]][posting_tuple_1[2]]["postings_list"], posting_list_dict[posting_tuple_2[1]][posting_tuple_2[2]]["postings_list"])
                first_merge = False
            else:
                posting_tuple_1 = heapq.heappop(postings_dict_size_heap)
                search_doc_id = self.merge_postings_list(search_doc_id, posting_list_dict[posting_tuple_1[1]][posting_tuple_1[2]]["postings_list"])

        # print("check:", search_doc_id)

        if len(search_doc_id) < max_k:
          
            #if no intersection found join all
            merge_iter = heapq.merge(*all_postings_list)
            prev = (-1, -1)
            dict_doc = {}
            if len(search_doc_id) > 0:
                for tuple in search_doc_id:
             
                    dict_doc[tuple[0]] = 1
           
            for idx, doc_tuple in enumerate(merge_iter):
           
                # if same document found add the scores and continue
                if prev[0] == doc_tuple[0]:
                    prev = (doc_tuple[0], doc_tuple[1] + prev[1])
                    continue
                else:
                   
                    if prev[0] > -1 and dict_doc.get(prev[0]) is None:
                        search_doc_id.append(prev)
                    prev = doc_tuple
            # Writing the last doc
            
            if prev[0] > -1 and dict_doc.get(prev[0]) is None:
                search_doc_id.append(prev)
          
        query_result = self.find_top_k(search_doc_id, max_k)

        return query_result

    def search(self, query):
        '''
        Perform a search
        '''

        start_time = time.perf_counter()
        query_dict = {}
        query = query.lower()
        query_backup_dict = {}
        # query_split = query.split()
        
        query_separate = query.split(",")
        k = 100
        if len(query_separate) == 2:
            k = int(query_separate[0])
            query = query_separate[1]
        else:
            query = query_separate[0]

        query_split = query.split(":")
        # default_dict = 
        if len(query_split) == 1:
            # not a field query
            # Search in page body as it contains all the content
            fields = ["b:", "t:", "i:"]
            for token in query_split[0].split():
                for category in fields:
                    if query_dict.get(self.query_categories[category]) is None:
                        query_dict[self.query_categories[category]] = []    
                    query_dict[self.query_categories[category]].append(self.stemmer.stemWord(token)) 
        
        else:
            # Field queries !!!!
            words = query.split()
            category_loop = "b:"
            first_token = True
            for token in words:
                for category in self.query_categories:        
                    if token is not None:    
                        if token.startswith(category):
                            category_loop = category
                            if query_dict.get(self.query_categories[category_loop]) is None:
                                query_dict[self.query_categories[category_loop]] = []    
                            if len(token) > 2:
                                token = token[2:]
                            else:
                                token = None

                if token is not None:
                    stem_word = self.stemmer.stemWord(token)
                    backup = []
                    for backup_category in ["b:", "i:", "t:"]:
                        if category_loop != backup_category:
                            if query_backup_dict.get(self.query_categories[backup_category]) is None:
                                query_backup_dict[self.query_categories[backup_category]] = []
                            query_backup_dict[self.query_categories[backup_category]].append(stem_word)
                        
                    if query_dict.get(self.query_categories[category_loop]) is None:
                        query_dict[self.query_categories[category_loop]] = []
                    query_dict[self.query_categories[category_loop]].append(stem_word)
                    # print(self.stemmer.stemWord(token))
        # print(query_dict)
        
        # Get postings list
        postings_list_dict = self.get_postings_list(query_dict)
        
        
        # Get query results 
        query_result = self.merge_postings_list_dict(postings_list_dict, k)

        if len(query_result) < k:

            backup_list_dict = self.get_postings_list(query_backup_dict)
        
            for category in postings_list_dict:
                for token in postings_list_dict[category]:
                    if token not in backup_list_dict:
                        if backup_list_dict.get(category) is None:
                            backup_list_dict[category] = {}
                        if backup_list_dict[category].get(token) is None:
                            backup_list_dict[category][token] = []
                        
                        backup_list_dict[category][token] = postings_list_dict[category][token]
                
            query_result = self.merge_postings_list_dict(backup_list_dict, k)
        
        end_time = time.perf_counter()
        
        elapsed_time = end_time - start_time
        
        top_k_titles = []
        for tuple in query_result:
            top_k_titles.append(linecache.getline(self.titles_file, tuple[0])[:-1])

        return query_result, top_k_titles, elapsed_time
      

    def write_search_result_file(self, all_results, all_titles, all_time, filename = "queries_op.txt"):
        '''
        Write to file
        '''
        fp = open(filename, "w+")

        for i in range(len(all_results)):
            N = len(all_results[i])
            for j in range(len(all_results[i])):
                string = "%d, %s\n" % (all_results[i][j][0], all_titles[i][j].lower())     
                fp.write(string)
            # Write time
            if N == 0:
                all_time[i] = 0
                N = 1
            string_time = "%f, %f \n \n" % (all_time[i], all_time[i] / N)
            fp.write(string_time)

    def search_from_file(self, filename, op_file = "queries_op.txt"):
        '''
        Search from file 
        '''
        with open(filename) as fp:
            lines = fp.readlines()
        

        all_results = []
        all_titles = []
        all_time = []

        for line in lines:
            result, titles, elapsed_time = self.search(line.split('\n')[0])
            all_results.append(result)
            all_titles.append(titles)
            all_time.append(elapsed_time)

        self.write_search_result_file(all_results, all_titles, all_time, op_file)
        

    def run(self):
        '''
        Run the search engine
        '''
        # print(self.tokens_dict)

        while True:
            
            query = input("\n$>")
            search_result = self.search(query)
            # print(search_result, "\n", len(search_result), "Search results")

            
if __name__ == "__main__":

    index_path = sys.argv[1]
    query_file = sys.argv[2]
    # query_output = sys.argv[3]
    # Search engine class
    search_engine = Engine(index_path)
    # Run the search engine
    # search_engine.run()
    if os.path.exists(query_file):
        # Search from file
        result = search_engine.search_from_file(query_file)
    else:
        # Search from query 
        result = search_engine.search(query_file)