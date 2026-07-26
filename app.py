import os

import cohere
import streamlit as st
from langchain_chroma import Chroma
from langchain_cohere import ChatCohere, CohereEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

st.set_page_config(page_title="Agente Santos Pegasus", page_icon="🤖")
st.title("🤖 Agente Santos Pegasus Soluciones")
st.caption(
    "Pregunta sobre onboarding, arquitectura de microservicios, incidentes, "
    "ingeniería back-end o front-end de la empresa."
)

COHERE_API_KEY = os.environ["COHERE_API_KEY"]
co = cohere.Client(COHERE_API_KEY)


@st.cache_resource
def load_vectorstore():
    embeddings = CohereEmbeddings(
        model="embed-multilingual-v3.0", cohere_api_key=COHERE_API_KEY
    )
    return Chroma(persist_directory="./chroma_db", embedding_function=embeddings)


vectorstore = load_vectorstore()
llm = ChatCohere(model="command-a-03-2025", temperature=0, cohere_api_key=COHERE_API_KEY)

prompt = ChatPromptTemplate.from_template(
    """Responde la pregunta basándote únicamente en el siguiente contexto extraído
de los documentos internos de Santos Pegasus Soluciones.
Si la respuesta no está en el contexto, dilo claramente en vez de inventar.

Contexto:
{context}

Pregunta: {question}"""
)


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def retrieve_with_rerank(pregunta, fetch_k=40, top_n=8):
    """
    1) Trae un grupo amplio de candidatos por similitud de embeddings.
    2) Usa Cohere Rerank para reordenarlos por relevancia real a la pregunta.
    """
    candidatos = vectorstore.similarity_search(pregunta, k=fetch_k)
    if not candidatos:
        return []
    resultado = co.rerank(
        model="rerank-v3.5",
        query=pregunta,
        documents=[doc.page_content for doc in candidatos],
        top_n=min(top_n, len(candidatos)),
    )
    return [candidatos[r.index] for r in resultado.results]


pregunta = st.text_input("Escribe tu pregunta:")

if st.button("Preguntar") and pregunta:
    with st.spinner("Buscando en los documentos..."):
        docs = retrieve_with_rerank(pregunta)
        contexto = format_docs(docs)
        cadena = prompt | llm | StrOutputParser()
        respuesta = cadena.invoke({"context": contexto, "question": pregunta})

    st.markdown("### Respuesta")
    st.write(respuesta)

    with st.expander("Fuentes consultadas"):
        for doc in docs:
            st.write(f"- {doc.metadata.get('source_file')} | página: {doc.metadata.get('page')}")
