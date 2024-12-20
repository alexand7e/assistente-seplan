import os
import streamlit as st
import pandas as pd
from google.generativeai import GenerativeModel
from google.generativeai import configure

# Definir o prompt para o modelo de IA
prompt = r"""
## Persona
Sou assistente financeiro que acompanha e monitora a execução orçamentária e financeira do Programa Pacto pelas Crianças

## Instruções
- Analise os relatórios {R1} e {R2} gerado pelo Sistema SIAFE contendo as informações referentes à execução orçamentária e financeira. 
- Compare os dados das colunas Unidade Gestora, Ação - 7600 , Plano Orçamentário - 287 ou 271, Dotação Atualizada, Despesas Empenhadas, Despesas Liquidadas, Despesas Pagas e Crédito Disponível.
- Apresente as Unidades Gestoras que contenham em {R2} valores  totais das respectivas colunas diferentes em {R1}.
- Apresente o resulto na forma de tabela.

## Exemplos de Interação
*Usuário:* Compare os dados das colunas Unidade Gestora,  Ação - 7600 , Plano Orçamentário - 287 ou 271, Dotação Atualizada, Despesas Empenhadas, Despesas Liquidadas, Despesas Pagas e Crédito Disponível.
*Assistente:* Tabela contendo a comparação entre as Unidades Gestores que tiveram modificação nos valores totais das colunas Unidade Gestora, Ação , Plano Orçamentário, Dotação Atualizada, Despesas Empenhadas, Despesas Liquidadas, Despesas Pagas e Crédito Disponível.

## Informações Adicionais
*Limitações:* Utilizar sempre dados dos relatórios contidos na pasta Pacto
*Diretrizes:* Sempre informe a data e o horário dos relatórios {R1} e {R2}.
"""

class GeminiModel:
    def __init__(self, api_key):
        configure(api_key=api_key)
        self.generation_config = {
            "temperature": 0.25,
            "top_p": 0.15,
            "top_k": 40,
            "max_output_tokens": 8000,
            "response_mime_type": "text/plain",
        }
        self.model = GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=self.generation_config,
            system_instruction=prompt,
        )

    def analyze_files(self, file1=None, file2=None, user_input=None):
        if user_input:
            # Incluir o contexto dos arquivos na mensagem
            message = {
                "role": "user",
                "parts": [
                    f"Usando os dados das planilhas fornecidas:\n\n{user_input}"
                ]
            }
            if file1 is not None and file2 is not None:
                message["parts"].append(f"\nDados da Planilha 1:\n{file1.head().to_string()}")
                message["parts"].append(f"\nDados da Planilha 2:\n{file2.head().to_string()}")
        else:
            message = {
                "role": "user",
                "parts": [f"Compare os relatórios entre os arquivos:\n{file1.head().to_string()}\n\ne\n\n{file2.head().to_string()}"]
            }

        try:
            response = self.model.generate_content(message)
            return response.text
        except Exception as e:
            return f"Erro ao processar a análise: {e}"

class StreamlitApp:
    def __init__(self):
        self.gemini_model = None
        if "excel_files" not in st.session_state:
            st.session_state["excel_files"] = {"file1": None, "file2": None}

    def run(self):
        st.title("Analisador de Planilhas com IA")

        # Gerenciar chave API com session_state
        if "api_key" not in st.session_state:
            st.session_state["api_key"] = None

        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        if not st.session_state["api_key"]:
            api_key = st.text_input("Insira sua chave API do Gemini:", type="password")
            if st.button("Salvar Chave API") and api_key:
                st.session_state["api_key"] = api_key
                st.success("Chave API salva com sucesso!")

        if st.session_state["api_key"]:
            if not self.gemini_model:
                self.gemini_model = GeminiModel(st.session_state["api_key"])
                st.success("API configurada com sucesso!")

            st.header("Upload de Planilhas")
            uploaded_files = st.file_uploader("Faça upload das duas planilhas para análise:", type=["xlsx"], accept_multiple_files=True)

            if uploaded_files and len(uploaded_files) == 2:
                file1 = pd.read_excel(uploaded_files[0])
                file2 = pd.read_excel(uploaded_files[1])

                st.session_state["excel_files"]["file1"] = file1
                st.session_state["excel_files"]["file2"] = file2

                st.write("Planilhas carregadas:")
                st.write(f"**Planilha 1:** {uploaded_files[0].name}")
                st.dataframe(file1.head())

                st.write(f"**Planilha 2:** {uploaded_files[1].name}")
                st.dataframe(file2.head())

                if st.button("Analisar Planilhas"):
                    with st.spinner("Analisando planilhas..."):
                        result = self.gemini_model.analyze_files(file1=file1, file2=file2)
                    st.subheader("Resultado da Análise")
                    st.write(result)
            elif uploaded_files and len(uploaded_files) < 2:
                st.warning("Por favor, faça upload de duas planilhas para análise.")

            st.header("Chat com a IA")
            user_input = st.text_input("Digite sua mensagem para a IA:")
            if st.button("Enviar Mensagem") and user_input:
                st.session_state["chat_history"].append({"role": "user", "content": user_input})
                try:
                    response = self.gemini_model.analyze_files(
                        file1=st.session_state["excel_files"]["file1"],
                        file2=st.session_state["excel_files"]["file2"],
                        user_input=user_input
                    )
                    st.session_state["chat_history"].append({"role": "assistant", "content": response})
                    st.write(response)
                except Exception as e:
                    st.error(f"Erro ao enviar mensagem: {e}")

        else:
            st.warning("Por favor, insira sua chave API para continuar.")

if __name__ == "__main__":
    app = StreamlitApp()
    app.run()
