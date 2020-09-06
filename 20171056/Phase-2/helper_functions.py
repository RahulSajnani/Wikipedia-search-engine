import re, os, linecache, gc
import heapq
import math

global categories, page_counter
categories = sorted(["references", "body", "infobox", "title", "category", "links"])
page_counter = 2000000

def read_token_line(line):

    words = line.split()
    if len(words) == 0:
        return None
    token_pair = (words[0], [])
    for i in range(1, len(words)):
        token_pair[1].append(int(words[i]))
    return token_pair


def merge_postings_list(postings_dict, repeated_dict_list):
    '''
    Merge two posting's list 
    '''

    combined_postings_list = {}

    for field in categories:
        doc_id_list = []
        combined_postings_list[field] = {}
        current_posting_list = [postings_dict[field]["postings_list"]]    
        for tokens_dict in repeated_dict_list:
            if len(tokens_dict[field]["postings_list"]) > 0:
                current_posting_list.append(tokens_dict[field]["postings_list"])

        merged_list = heapq.merge(*current_posting_list)
        
        for idx, doc_pair in enumerate(merged_list):
            doc_id_list.append(doc_pair)
        
        
        if len(doc_id_list):
            combined_postings_list[field]["postings_list"] = doc_id_list
        else:
            combined_postings_list[field]["postings_list"] = []

        
    return combined_postings_list

def pop_token(heap, file_pointers):
    '''
    '''
    token_pair = heapq.heappop(heap)
    fp = file_pointers[token_pair[1][-1]]

    read_token = read_token_line(fp.readline())
    if read_token is not None:
        read_token[1].append(token_pair[1][-1])
        heapq.heappush(heap, read_token)
    else:
        fp.close()

    return token_pair

def decode_line(line):
    '''
    Decode line from the file containing posting's list
    '''
    
    line_dict = {}
    line = line.split()
    
    # line_dict["size"] = int(line[0])
    line_dict["postings_list"] = []
    
    for i in range(0, len(line), 2):
        line_dict["postings_list"].append((int(line[i]), int(line[i + 1])))

    return line_dict

def get_all_postings_list(token_pair, files_dictionary):

    token_dictionary = {}
    for field in categories:
        if files_dictionary.get(field) is not None:
            if token_pair[1][categories.index(field)] != 0:
                file_name = files_dictionary[field][token_pair[1][-1]]
                line = linecache.getline(file_name, int(token_pair[1][categories.index(field)]))
                token_dictionary[field] = decode_line(line)
            else:
                token_dictionary[field] = {"postings_list": []}

        else:
            token_dictionary[field] = {"postings_list": []}

    return token_dictionary

def write_posting_dict(token, posting_dict, file_output_pointers):

    token_write_string = str(token)
    # print(posting_dict)
    for field in categories:
        
        df = len(posting_dict[field]["postings_list"])
        if df:
            write_string = ""

            for tuple_iter in posting_dict[field]["postings_list"]:
                write_string += "%d %.2f " % (tuple_iter[0], (math.log((1 + tuple_iter[1]), 10) * math.log(page_counter / df, 10)))
            write_string += "\n"

            line = file_output_pointers[field][1]
            file_output_pointers[field][0].write(write_string)
            file_output_pointers[field][1] = line + 1
            token_write_string += " %d" % line
        else:
            token_write_string += " 0"
    token_write_string += "\n"
    # print(token_write_string)
    file_output_pointers["tokens"][0].write(token_write_string)
    file_output_pointers["tokens"][1] += 1

def merge_files(files_dictionary,  output_directory):
    
    
    token_files = files_dictionary["tokens"]
    file_pointers = []
    tokens_heap = []
    file_output_pointers = {}
    
    if not os.path.exists(output_directory):
        # os.rmdir(output_directory)
        os.makedirs(output_directory)

    for field in categories:
        file_output_pointers[field] = [open(os.path.join(output_directory, ("index_%s.txt" % str(field))), "w"), 1]
    file_output_pointers["tokens"] = [open(os.path.join(output_directory, "tokens.txt"), "w"), 1]

    del(files_dictionary["tokens"])
    
    for token_file_name in token_files:
        fp = open(token_file_name, "r")
        token_pair = read_token_line(fp.readline())
        file_pointers.append(fp)
        if token_pair:
            token_pair[1].append(len(file_pointers) - 1)
        heapq.heappush(tokens_heap, token_pair)
        
    while len(tokens_heap) > 0:
        
        token_pair = pop_token(tokens_heap, file_pointers)
        posting_dict = get_all_postings_list(token_pair, files_dictionary)
        repeated_token_list = []
        # print(posting_dict)
        # print(token_pair[0])
        if len(tokens_heap):
            while token_pair[0] == tokens_heap[0][0]:
                token_pair_2 = pop_token(tokens_heap, file_pointers)
                posting_dict_2 = get_all_postings_list(token_pair_2, files_dictionary)
                repeated_token_list.append(posting_dict_2)
                # posting_dict = merge_postings_list(posting_dict, posting_dict_2)
            if len(repeated_token_list):
                merged_dict = merge_postings_list(posting_dict, repeated_token_list)
                posting_dict = merged_dict
        
        write_posting_dict(token_pair[0], posting_dict, file_output_pointers)

        repeated_token_list.clear()
    # print("end")


if __name__=="__main__":

    files_dictionary = {"tokens": ["tokens_0.txt", "tokens_1.txt", "tokens_2.txt"], "body": ["index_body_0.txt", "index_body_1.txt", "index_body_2.txt"]}
    for field in files_dictionary:
        for i in range(len(files_dictionary[field])):
            files_dictionary[field][i] = os.path.join("./search_index/", files_dictionary[field][i])
    merge_files(files_dictionary, "./combined_index")
    pass