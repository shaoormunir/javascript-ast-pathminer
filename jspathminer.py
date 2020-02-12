import json
import esprima
from tqdm import tqdm
import pickle
import os


class DocumentContext:
    def __init__(self):
        self.start_token_ids = []
        self.end_token_ids = []
        self.path_ids = []
        self.document_path = ""
        self.document_label = ""
        self.document_id = 0

    def print(self):
        print(f"#{self.document_id}")
        print(f"label:{self.document_label}")
        print(f"path:{self.document_path}")
        print("paths:")
        for start, end, path in zip(self.start_token_ids, self.end_token_ids, self.path_ids):
            print(f"{start}\t{path}\t{end}")


class PathContext:
    def __init__(self, start_token=""):
        self.start_token = start_token
        self.path = ""
        self.end_token = ""
        self.complete_context = False

    def print(self):
        print(f"{self.start_token} | {self.path} | {self.end_token}")


def get_data_type_expression(data, expression):
    symbol = ""
    if expression == "BinaryExpression":
        if data['operator'] == '+':
            symbol = ":SUM"
        if data['operator'] == '-':
            symbol = ":SUB"
        if data['operator'] == '*':
            symbol = ":MUL"
        if data['operator'] == '/':
            symbol = ":DIV"
        if data['operator'] == '%':
            symbol = ":MOD"

    if expression == "LogicalExpression":
        if data['operator'] == '||':
            symbol = ":OR"
        if data['operator'] == '&&':
            symbol = ":AND"

    return expression+symbol


def get_new_path_context(start_token):
    path_context = PathContext(start_token)
    return path_context


def recursive_traverse(data, contexts, up):
    if isinstance(data, dict):
        if len(contexts) == 0:
            contexts.append(PathContext())
        if contexts[len(contexts)-1].start_token == "" and data.get('type', '') == 'Identifier':
            contexts[len(contexts)-1].start_token = data.get('name', '')
            contexts[len(contexts)-1].path = f"{data.get('type', '')} ↑"
            return contexts, True

        if not contexts[len(contexts)-1].complete_context and data.get('type', '') == 'Identifier':
            if (contexts[len(contexts)-1].complete_context):
                contexts.append(get_new_path_context(
                    contexts[len(contexts)-1].start_token))
            contexts[len(contexts)-1].end_token = data.get('name', '')
            contexts[len(contexts)-1].path += f" {data.get('type', '')}"
            contexts[len(contexts)-1].complete_context = True
            contexts.append(get_new_path_context(data.get('name', '')))
            contexts[len(contexts)-1].path = f"{data.get('type', '')} ↑"
            return contexts, False

        if not contexts[len(contexts)-1].complete_context  and data.get('type', '') == 'Literal':
            if (contexts[len(contexts)-1].complete_context):
                contexts.append(get_new_path_context(
                    contexts[len(contexts)-1].start_token))
            contexts[len(contexts)-1].end_token = data.get('value', '')
            contexts[len(contexts)-1].path += f" {data.get('type', '')}"
            contexts[len(contexts)-1].complete_context = True
            contexts.append(PathContext())
            # print(path)
            return contexts, False
        for key, value in data.items():
            temp_path =  contexts[len(contexts)-1].path
            contexts, up = recursive_traverse(value, contexts, up)
            if (not contexts[len(contexts)-1].complete_context) and (temp_path != contexts[len(contexts)-1].path):
                if up:
                    contexts[len(contexts)-1].path += f" {get_data_type_expression(data, data.get('type', ''))} ↑"
                else:
                    contexts[len(contexts)-1].path += f" {get_data_type_expression(data, data.get('type', ''))} ↓"

    elif isinstance(data, list):
        for item in data:
            recursive_traverse(item, contexts, up)
    return contexts, up


class PathMiner:
    def __init__(self, folder_path, output_path, checkpoint_after=200, label_dict = {}):
        self.folder_path = folder_path
        self.output_path = output_path
        self.checkpoint_after = checkpoint_after
        self.label_dict = label_dict

    def mine_paths(self):
        doc_contexts = []
        path_idx = {}
        terminal_idx = {}
        files = [os.path.join(path, name) for path, subdirs, files in os.walk(self.folder_path) for name in files]

        print(files)
        for i, js_file in enumerate(tqdm(files)):
            try:
                with open(js_file) as f:
                    data = f.read()

                    json_text = json.dumps(esprima.parseScript(data).toDict())
                    json_data = json.loads(json_text)

                    contexts, _ = recursive_traverse(
                        json_data, [], False)

                    doc_context = DocumentContext()
                    doc_context.document_path = js_file
                    if js_file in self.label_dict:
                        doc_context.document_label = self.label_dict[js_file]
                    doc_context.document_id = len(doc_contexts)

                    for context in contexts:
                        if not (isinstance(context.end_token, dict) or isinstance(context.start_token, dict) or isinstance(context.path, dict)) and not (context.end_token == "" or context.start_token == "" or context.path == ""):
                            if context.start_token not in terminal_idx:
                                terminal_idx[context.start_token] = len(terminal_idx)
                            if context.end_token not in terminal_idx:
                                terminal_idx[context.end_token] = len(terminal_idx)
                            if context.path not in path_idx:
                                path_idx[context.path] = len(path_idx)

                            doc_context.start_token_ids.append(
                                terminal_idx[context.start_token])
                            doc_context.end_token_ids.append(
                                terminal_idx[context.end_token])
                            doc_context.path_ids.append(path_idx[context.path])
                    doc_contexts.append(doc_context)

            except IOError:
                print(f"Cannot open file : {js_file}")
            except Exception as e:
                print(f"Error in file: {js_file} due to {e}")

            if i % self.checkpoint_after == 0 and i != 0:
                with open(self.output_path+"doc_contexts_checkpoint_" + i + ".pkl", "wb") as f:
                    pickle.dump(doc_contexts, f)
                with open(self.output_path+"terminal_idx_checkpoint_"+i+".pkl", "wb") as f:
                    pickle.dump(terminal_idx, f)
                with open(self.output_path+"path_idx_checkpoint_"+i+".pkl", "wb") as f:
                    pickle.dump(path_idx, f)
                    
        with open(self.output_path+"doc_contexts_checkpoint_final.pkl", "wb") as f:
            pickle.dump(doc_contexts, f)
        with open(self.output_path+"terminal_idx_checkpoint_final.pkl", "wb") as f:
            pickle.dump(terminal_idx, f)
        with open(self.output_path+"path_idx_checkpoint_final.pkl", "wb") as f:
            pickle.dump(path_idx, f)

        return doc_contexts, terminal_idx, path_idx

miner = PathMiner("test/", "test_output/" ,label_dict={"test/test.js": "marketing", "test/test2.js": "cdn"})
doc_contexts, terminal_idx, path_idx = miner.mine_paths()

for context in doc_contexts:
    context.print()

print (terminal_idx)
print (path_idx)