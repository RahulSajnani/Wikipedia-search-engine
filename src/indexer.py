# import nltk
import xml.etree.ElementTree as etree
import sys
import helper_functions
import re
import Stemmer
import heapq

'''
Author: Rahul Sajnani
'''


class Indexer:
    '''
    Wikipedia dump indexer class

    Creates index for given XML file
    '''
    
    def __init__(self, xml_file_path, stop_words_file = "./stopwords.txt"):

        self.parser = etree.iterparse(xml_file_path, events = ("start", "end"))
        
        # Reading stop words list
        with open(stop_words_file, "r") as fp:
            self.stop_words = fp.readlines()
        
        # print(self.stop_words)
        self.stop_words_dict = {}
        # self.stop_words = [word.strip("'") for word in self.stop_words]
        for word in self.stop_words:
            self.stop_words_dict[word.split("\n")[0]] = 1

        self.stemmer = Stemmer.Stemmer('english')
        self.postings_dictionary = dict()

    def process_page(self, page_dict):
        '''
        Removes stop words and tokenizes
        '''
        
        tokens_dict = {}

        for key in page_dict:    
            if key != "id":
                string = page_dict[key]
                tokens_dict[key] = dict()
                # Case folding
                string = string.lower()
                # Removing special symbols
                string = re.sub(r'[^A-Za-z0-9]+', r' ', string)
                string = string.split()
                
                for word in string:
                    # if word not in self.stop_words:
                    if self.stop_words_dict.get(word) is None:    
                        word = self.stemmer.stemWord(word)
                        if tokens_dict[key].get(word) is not None:
                            tokens_dict[key][word] += 1
                        else:
                            tokens_dict[key][word] = 1

        return tokens_dict        

    def process_tokens_dict(self, id, tokens_dict):
        '''
        Create posting list from tokens dictionary 
        '''
        # postings_dict = {}

        for key in tokens_dict.keys():
            if self.postings_dictionary.get(key) is None:
                self.postings_dictionary[key] = {}
            
            for token in tokens_dict[key]:
                
                if self.postings_dictionary[key].get(token) is None:
                    self.postings_dictionary[key][token] = []
                
                heapq.heappush(self.postings_dictionary[key][token], (id, tokens_dict[key][token]))
        
        # return postings_dict
        

    def create_postings_list(self, page_dictionary):
        '''
        Extracts infobox, category, links, and references
        '''
        # infobox and external links required

        
        page_body = page_dictionary["body"]
        # pattern = re.compile('<nowiki([> ].*?)(</nowiki>|/>)', re.DOTALL)
        if page_body is not None:
            page_references = " ".join(re.findall("<ref>(.*?)</ref>", page_body))
            page_infobox = " ".join(re.findall("\{\{Infobox (.*?)\}\}", page_body))
            page_category = " ".join(re.findall("\[\[Category:(.*?)\]\]", page_body))
            # external_links = pattern.findall(page_body)
            # print(external_links)
            page_dictionary["category"] = page_category
            page_dictionary["infobox"] = page_infobox
            page_dictionary["references"] = page_references

        
        tokens_dict = self.process_page(page_dictionary)
        self.process_tokens_dict(page_dictionary["id"], tokens_dict)
        # print(self.postings_dictionary)  

        pass



    def run(self):
        '''
        Run indexer
        '''

        page_counter = 0
        tags_list = []
        
        for event, element in self.parser:
            
            tag_name = element.tag.split("}")[-1]    
            
            if event == "start":

                tags_list.append(tag_name)
                if tag_name == "page":
            
                    page_dict = {}
                    page_title = ""
                    page_id = -1
                    page_body = ""                    
                        
            elif event == "end":
                
                tags_list.pop()

                if tag_name == "id" and tags_list[-1] == "page":
                        # update id if page is detected but is not revision page       
                        page_id = int(element.text)
                       
                elif tag_name == "title":
                        page_title = element.text
                    
                elif tag_name == "text":
                        page_body = element.text
                    
                elif tag_name == "page":    
                    page_counter += 1
                    # print(page_id, " ", page_title)
                    page_dict = {"id": page_id, "title": page_title, "body": page_body}
                    self.create_postings_list(page_dict)

                # Clearing element  
                element.clear()

            last_tag = tag_name

        print(page_counter)

        max_len = 0
        max_token = 0
        for key in (self.postings_dictionary):
            for token in sorted(self.postings_dictionary[key]):
                length_list = len(self.postings_dictionary[key][token])
                if length_list > max_len:
                    max_len = length_list
                    max_token = token

        print(max_token, max_len)


if __name__ == "__main__":

    wikipedia_dump_path = sys.argv[1]
    index_path = sys.argv[2]

    indexer = Indexer(wikipedia_dump_path)
    indexer.run()
    # print(wikipedia_dump_path)