import re
from openai import OpenAI
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from datasets import load_dataset
from sentence_transformers import util
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY)
    api_key="sk-kwW1BsPpbbLfLDFBNmByeYYjIBqnACvv6TyuL8IQN7FRnUID",
    base_url="https://api.ephone.chat/v1"
)
def normalize_answer(s):
    """Lower text and remove punctuation, articles and extra whitespace."""
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)

    def white_space_fix(text):import re
import string
from collections import Counter

# 数据预处理函数
def normalize_answer(s):
    """Lower text and remove punctuation, articles and extra whitespace."""
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)

    def white_space_fix(text):
        return ' '.join(text.split())

    def remove_punctuation(text):
        return ''.join(ch for ch in text if ch not in set(string.punctuation))

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punctuation(lower(s))))


def f1_score(prediction, ground_truth):
    prediction_tokens = normalize_answer(prediction).split()
    ground_truth_tokens = normalize_answer(ground_truth).split()
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(prediction_tokens)
    recall = num_same / len(ground_truth_tokens)
    f1 = 2 * precision * recall / (precision + recall)
    return f1
def context_extension(context):
    prompt = f"""
    Context information is below .
    ---------------------
    {context}
    ---------------------
    You are a Professor who is proficient in asking questions. Your task is to set up 6 questions for students to answer based on the provided context.
    1.The questions should be diverse in nature and cover various aspects of the document. Ensure that they include the words "who," "where," "what," "when," "why," and "how."
    2.Restrict the questions to the information provided , and avoid ambiguous references .
    Output Format :
    [
    "question " ,
    "question " ,
    ]
        """
    response3 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
        ]
    )
    return response3.choices[0].message.content

def extension(topic):#扩展query
    prompt=f"""
    Context information is below .
    ---------------------
    {topic}
    ---------------------
    Given the context information and not prior knowledge , generate only questions based on the below query .
    You are a Professor who is proficient in asking questions. Your task is to setup 6 questions for students to answer.
    1.The questions should be diverse in nature across the document.At least it should includes”who,where,what,when,why,how”these six directions.
    2.Restrict the questions to the information provided , and avoid ambiguous references .
    Output Format :
    [
    " question " ,
    " question " ,
    ]
    """
    response2 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
        ]
    )
    return response2.choices[0].message.content

def standardization(query):#主题提取
    prompt = f"""
    The context you get is below
    -------------------------------------------------------
    {query}
    -------------------------------------------------------
    You are a Professor of Semantic recognition. Your task is to extract the topic of the context and what you need to do is below.
    1.You need to extract a topic sentence from the context, remove redundant modifiers and try to retain key elements in the context.
    2.The topic sentence must be a declarative sentence and summarize the context.
    3.The topic sentence should be short without any redundant content.
    4.Avoid the topic sentence being irrelevant to the context or as same as the context.
    the example is below.
    Context: Please talk about the advantages of AI medicine.
    Your output: The advantages of AI medicine.

    Output Format:
    [
    "topic sentence"
    ]
    """
    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": prompt},
    ]
)
    return response.choices[0].message.content

#query=input()
dataset = load_dataset("squad_v2")
queries = []
answers = []
contexts = []
for idx, example in enumerate(dataset["train"]):  # 遍历训练集中的所有样本
    context = example.get("question", "").strip()  # 提取 'query' 作为上下文
    context3 = example.get("context", "").strip()
    answerx = example.get("answers", "")
    answer = answerx.get("text", [])
    if context:  # 确保不为空
        queries.append(context)
        answers.append(answer)
        contexts.append(context3)
count = 0
f1sc = []
total = 0

context_embeddings = model.encode(contexts)

# 构建 FAISS 索引
dimension = context_embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(context_embeddings))

for i in range(len(queries)):
    query = queries[i]
    answer = answers[i][0]
    print(query)
    topic = standardization(query)
    print(topic)  # 输出主题
    response_text = eval(extension(topic))  # 生成问题组并格式转换
    querygroup = response_text
    print(querygroup)  # 输出转换格式后的问题组

    group_embeddings = model.encode(querygroup)  # 对问题组进行初步编码
    group_embeddings.shape
    # print(group_embeddings)
    query_embedding = model.encode(query)  # 对用户的初始query进行编码生成向量
    '''------------------------------------------------
    #下方为测试代码，仅用于测试query与querygroup各问题的相似性
    for embedding, sentence in zip(group_embeddings, querygroup):
        similarity = util.pytorch_cos_sim(query_embedding, embedding)
        #余弦相似度计算
        print(similarity, sentence)
    -------------------------------------------------'''

    pooled_group_embedding = np.mean(group_embeddings, axis=0)  # 对group进行平均池化
    # print(pooled_group_embedding)
    # print(query_embedding)
    # similarity = util.pytorch_cos_sim(query_embedding, pooled_group_embedding)#group平均池化后与query的余弦相似度计算
    # print(similarity)
    '''RAG流程正式开始'''


    # 用 pooled_group_embedding 进行初步检索，找出前十个最相似的文本向量
    k = 10  # 检索前10个
    distances, indices = index.search(np.array([pooled_group_embedding]), k)
    # 用 query_embedding 找到余弦相似度最高的文本
    retrieved_texts = [contexts[i] for i in indices[0]]
    retrieved_embeddings = [context_embeddings[i] for i in indices[0]]
    similarities = [util.pytorch_cos_sim(query_embedding, embedding).item() for embedding in retrieved_embeddings]

    # 找出相似度最高的文本
    max_similarity_idx = np.argmax(similarities)
    best_context = retrieved_texts[max_similarity_idx]
    print("最相似的上下文: ", best_context, "\n")
    print("最相似的answer: ", answer, "\n")
    input_text = f"Context: {best_context}\nQuestion: {query}\nprompt:Your answer only needs to contain the answer to my question, and you don't need to include the reason or redundant information in the context that has nothing to do with the question. Try to be as concise and accurate as possible."
    re1 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": input_text},
        ]
    )
    ans = re1.choices[0].message.content
    print(ans,"\n")
    predictions = ans
    ground_truths = answer
    results = f1_score(predictions, ground_truths)
    total += results
    count += 1
    print(f"F1 Score: {results}\n")
    print(f"average F1 Score: {total/count}\n")