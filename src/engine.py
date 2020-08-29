import xml.etree.ElementTree as etree
import sys
import helper_functions
import re
import Stemmer
import os
import linecache

'''
Author: Rahul Sajnani
'''


class Engine:
    '''
    Search engine class
    
    '''

    def __init__(self, index_path):
        super().__init__()

        self.index_path = index_path
        self.categories = sorted(["references", "body", "infobox", "title", "category"])
        self.query_categories = {"c:": "category", "b:": "body", "t:": "title", "i:": "infobox", "r:": "references"}
        self.tokens_dict = self.get_tokens()
        self.stemmer = Stemmer.Stemmer("english")
        
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

    def decode_line(self, line):
        '''
        Decode line from the file containing posting's list
        '''
        
        line_dict = {}
        line = line.split()
        
        line_dict["size"] = line[0]
        line_dict["postings_list"] = []
        for i in range(1, len(line), 2):
            line_dict["postings_list"].append((line[i], line[i + 1]))

        return line_dict


    def get_postings_list(self, query_dict):
        '''
        Get the index files
        '''
        
        postings_list = {}
        for category in query_dict:
            filename = "index_%s.txt" % str(category)
            filename = os.path.join(self.index_path, filename)
            
            for token in query_dict[category]:
                
                # If token in dictionary
                if (self.tokens_dict.get(token) is not None):
                    # If token is present in the respective category
                    if self.tokens_dict[token][self.categories.index(category)] != "-1": 
                        # Get line :)
                        postings_list_dict = self.decode_line(linecache.getline(filename, int(self.tokens_dict[token][self.categories.index(category)])))

                        if postings_list.get(category) is None:
                            postings_list[category] = {}
                        postings_list[category][token] = postings_list_dict
                        # print(line, category)
        
        return postings_list

    def merge_postings_list(self, list_posting_list):
        '''
        Merges dictionary of postings list for a query
        '''

        pass

    def search(self, query):
        '''
        Perform a search
        '''

        query_dict = {}
        query_split = query.split()
        
        for token in query_split:
            token = token.lower()
            found = False
            for category in self.query_categories:
                if token.startswith(category):
                    found = True
                    if query_dict.get(self.query_categories[category]) is None:
                        query_dict[self.query_categories[category]] = []    
                    query_dict[self.query_categories[category]].append(self.stemmer.stemWord(token[2:]))
            
            # if category is not found
            if not found:
                for category in self.query_categories:
                    if query_dict.get(self.query_categories[category]) is None:
                        query_dict[self.query_categories[category]] = []    
                    query_dict[self.query_categories[category]].append(self.stemmer.stemWord(token))
                
        # print(query_dict)
        postings_list_dict = self.get_postings_list(query_dict)
        query_result = self.merge_postings_list(postings_list_dict)
        
        return query_result

    def run(self):
        '''
        Run the search engine
        '''
        # print(self.tokens_dict)

        while True:
            
            query = input("\n$>")
            query_result = self.search(query)
            print(query_result, "\n")

            
if __name__ == "__main__":

    index_path = sys.argv[1]

    search_engine = Engine(index_path)

    # Run the search engine
    search_engine.run()