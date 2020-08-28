try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

import sys
import helper_functions
import re
import Stemmer
import heapq
import os

'''
Author: Rahul Sajnani
'''


class Indexer:
    '''
    Wikipedia dump indexer class

    Creates index for given XML file
    '''
    
    def __init__(self, xml_file_path, index_directory, stop_words_file = "./stopwords.txt"):

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
        self.index_directory = index_directory

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
                    if key != "title":
                        if self.stop_words_dict.get(word) is None:    
                            word = self.stemmer.stemWord(word)
                            if tokens_dict[key].get(word) is not None:
                                tokens_dict[key][word] += 1
                            else:
                                tokens_dict[key][word] = 1
                    else:
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

        for key in tokens_dict:
            if self.postings_dictionary.get(key) is None:
                self.postings_dictionary[key] = {}
            
            for token in tokens_dict[key]:
                
                if self.postings_dictionary[key].get(token) is None:
                    self.postings_dictionary[key][token] = []
                
                self.postings_dictionary[key][token].append((id, tokens_dict[key][token]))
                # heapq.heappush(self.postings_dictionary[key][token], (id, tokens_dict[key][token]))
        
        # return postings_dict
        

    def create_postings_list(self, page_dictionary):
        '''
        Extracts infobox, category, links, and references
        '''
        # infobox and external links required

        
        page_body = page_dictionary["body"]
        # pattern = re.compile('<nowiki([> ].*?)(</nowiki>|/>)', re.DOTALL)
        if page_body is not None:
            # removing comments
            page_body = re.sub('<!--.*?-->',' ',page_body,flags = re.DOTALL)
            # removing math equations
            page_body = re.sub('<math([> ].*?)(</math>|/>)',' ',page_body,flags = re.DOTALL)
            # removing files
            page_body = re.sub('\[\[([fF]ile:|[iI]mage)[^]]*(\]\])',' ',page_body,flags = re.DOTALL)
            # obtaining references
            page_references = " ".join(re.findall("<ref>(.*?)</ref>", page_body))
            # obtaining infobox
            page_infobox = " ".join(re.findall("\{\{Infobox (.*?)\}\}", page_body, flags = re.DOTALL))
            # obtaining categories
            page_category = " ".join(re.findall("\[\[Category:(.*?)\]\]", page_body))
            # external_links = pattern.findall(page_body)
            page_body = re.sub('<.*?>',' ',page_body,flags = re.DOTALL)
            # page_body = re.sub('\{\{([^}{]*)\}\}',' ',page_body,flags = re.DOTALL)
            page_body = re.sub('\{\{([^}]*)\}\}',' ',page_body,flags = re.DOTALL)
            # # print(external_links)
            page_dictionary["category"] = page_category
            page_dictionary["infobox"] = page_infobox
            page_dictionary["references"] = page_references

            # page_body = re.sub(r"(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)", r" ", page_body)

            page_dictionary["body"] = page_body

        tokens_dict = self.process_page(page_dictionary)
        self.process_tokens_dict(page_dictionary["id"], tokens_dict)
        # print(self.postings_dictionary)  

        pass

    def write_index(self):
        '''
        Writing index to respective files
        '''
        dict_lines = {}
        if not os.path.exists(self.index_directory):
            os.makedirs(self.index_directory)

        for key in (self.postings_dictionary):
            dict_lines[key] = {}
            filename = "index_%s.txt" % str(key)
            fp = open(os.path.join(self.index_directory, filename), "w")
            line = 1
            write_string = ""
            for token in sorted(self.postings_dictionary[key]):
                # get length of posting list
                length_list = len(self.postings_dictionary[key][token])
                write_string += str(length_list)
                for tuple_iter in sorted(self.postings_dictionary[key][token]):
                    # Writing doc id and frequency
                    write_string += " %s %s" % (str(tuple_iter[0]), str(tuple_iter[1]))
                dict_lines[key][token] = line
                line += 1
                write_string += "\n"

                # Write to file if the lines are more than 5000 and clear
                if line % 5000 == 0:
                    fp.write(write_string)
                    write_string = ""

            if write_string != "":
                fp.write(write_string)
            
            fp.close()

        
        for key in sorted(dict_lines):
            filename = "tokens_%s.txt" % str(key)
            fp = open(os.path.join(self.index_directory, filename), "w")
            line = 1
            write_string = ""
            for token in (dict_lines[key]):
                # get length of posting list
                line += 1
                write_string += "%s %s" % (str(token), str(dict_lines[key][token]))
                write_string += "\n"

                # Write to file if the lines are more than 5000 and clear
                if line % 10000 == 0:
                    fp.write(write_string)
                    write_string = ""
            if write_string != "":
                fp.write(write_string)
                
            fp.close()
        

    def run(self):
        '''
        Run indexer
        '''

        page_counter = 0
        tags_list = []
        
        first = True
        root = 0

        for event, element in self.parser:
            
            tag_name = element.tag.split("}")[-1]    
            if event == "start":
                
                tags_list.append(tag_name)
                
                # Saving root element to clear in element tree
                if first:
                    first = False
                    root = element
                    
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
                    root.clear()
                # Clearing element  
                element.clear()

            last_tag = tag_name

        print(page_counter)

        self.write_index()

        # max_len = 0
        # max_token = 0
        # for key in (self.postings_dictionary):
        #     for token in sorted(self.postings_dictionary[key]):
        #         length_list = len(self.postings_dictionary[key][token])
        #         if length_list > max_len:
        #             max_len = length_list
        #             max_token = token

        # print(max_token, max_len)


if __name__ == "__main__":

    wikipedia_dump_path = sys.argv[1]
    index_path = sys.argv[2]

    indexer = Indexer(wikipedia_dump_path, index_directory=index_path)
    indexer.run()
    # print(wikipedia_dump_path)