# Processador de Arquivos BibTeX

Este script Python (`bibtex_processor.py`) foi projetado para automatizar o processamento de arquivos BibTeX, incluindo padronização de entradas, remoção de duplicatas baseadas em DOI e conversão para o formato CSV.

## Funcionalidades

1.  **Padronização de BibTeX:**
    *   Lê arquivos `.bib` de um diretório de entrada (`input_bib/` por padrão).
    *   Converte todos os nomes de campos (chaves) para minúsculas (exceto `ID` e `ENTRYTYPE` que são preservados).
    *   Garante a presença de campos essenciais (definidos na lista `essential_fields` dentro da função `standardize_bibtex_file`), preenchendo com strings vazias se ausentes.
    *   **Normaliza o campo `doi`:** Extrai apenas o identificador DOI (ex: `10.1109/abc.123`), mesmo que o campo original contenha uma URL completa (ex: `https://doi.org/10.1109/abc.123`). A normalização também converte o DOI para minúsculas para comparação consistente.
    *   Consolida `booktitle` no campo `journal` se `journal` estiver vazio.
    *   Salva os arquivos padronizados em um diretório de saída (`standardized_bib/` por padrão).

2.  **Remoção de Duplicatas por DOI:**
    *   Compara um arquivo BibTeX padronizado (arquivo "X") com outro (arquivo "Y").
    *   Remove as entradas do arquivo X cujo DOI (normalizado e em minúsculas) já existe no arquivo Y.
    *   Salva o resultado (arquivo X sem as duplicatas encontradas em Y) em um diretório de processados (`processed_bib/` por padrão).
    *   **Nota:** A lógica de comparação no exemplo padrão (`if __name__ == "__main__":`) compara cada arquivo X (SciDirect, MDPI) *separadamente* contra o arquivo Y (IEEE). Para uma remoção acumulada (ex: remover de MDPI o que existe em IEEE *ou* SciDirect), você precisará ajustar esta seção para carregar DOIs de múltiplos arquivos Y ou processar os arquivos sequencialmente.

3.  **Conversão para CSV:**
    *   Converte um arquivo BibTeX (geralmente o resultado da remoção de duplicatas) para o formato CSV.
    *   Gera um arquivo CSV com as seguintes colunas: `ID`, `doi`, `classification`, `title`, `abstract`, `keywords`, `Review`, `author`, `year`, `Publisher`, `journal`, `type title`.
    *   As colunas `classification` e `Review` são preenchidas com strings vazias, conforme solicitado.
    *   O campo `type title` no CSV corresponde ao `ENTRYTYPE` original do BibTeX (em minúsculas).
    *   Salva os arquivos CSV em um diretório de saída (`output_csv/` por padrão).

## Pré-requisitos

*   Python 3.x
*   Biblioteca `bibtexparser`: Instale usando pip:
    ```bash
    pip install bibtexparser
    ```

## Estrutura de Diretórios Esperada

O script espera a seguinte estrutura de diretórios no mesmo local onde ele é executado:

```
.
├── bibtex_processor.py
├── input_bib/             # Coloque seus arquivos .bib de entrada aqui
│   ├── arquivo1.bib
│   └── arquivo2.bib
├── standardized_bib/      # Saída dos arquivos padronizados (criado automaticamente)
├── processed_bib/         # Saída dos arquivos após remoção de duplicatas (criado automaticamente)
└── output_csv/            # Saída dos arquivos CSV finais (criado automaticamente)
```

## Como Usar

1.  **Preparar Arquivos de Entrada:** Coloque todos os seus arquivos BibTeX (`.bib`) que você deseja processar dentro do diretório `input_bib/`.

2.  **Configurar o Script (se necessário):**
    *   Abra o arquivo `bibtex_processor.py` em um editor de texto.
    *   Vá até a seção final do script, dentro do bloco `if __name__ == "__main__":`.
    *   **Ajuste os Nomes dos Arquivos:** Modifique as variáveis `*_input`, `*_standardized`, `file_x_*`, `file_y_*`, `processed_*`, `final_bib_for_csv`, `output_csv_file`, etc., para refletir os nomes dos seus arquivos de entrada e os nomes desejados para os arquivos de saída.
    *   **Ajuste a Lógica de Processamento:** Modifique as chamadas das funções (`standardize_bibtex_file`, `remove_duplicates_by_doi`, `convert_bibtex_to_csv`) para implementar o fluxo exato que você precisa. Por exemplo:
        *   Se você tiver mais arquivos de entrada, adicione chamadas `standardize_bibtex_file` para cada um.
        *   Se você quiser comparar `arquivoA.bib` contra `arquivoB.bib` e `arquivoC.bib`, você precisará carregar os DOIs de B e C em um único conjunto (`dois_y`) antes de chamar `remove_duplicates_by_doi` para o arquivo A, ou processar sequencialmente (remover duplicatas de A vs B, depois remover duplicatas do resultado vs C).
        *   Decida qual(is) arquivo(s) BibTeX processado(s) você deseja converter para CSV e ajuste a chamada `convert_bibtex_to_csv`.

3.  **Executar o Script:** Abra um terminal ou prompt de comando, navegue até o diretório onde o script `bibtex_processor.py` está localizado e execute:
    ```bash
    python3 bibtex_processor.py
    ```

4.  **Verificar os Resultados:** Após a execução, verifique os diretórios `standardized_bib/`, `processed_bib/`, e `output_csv/` para encontrar os arquivos gerados.

## Exemplo de Fluxo (Padrão no Script)

O fluxo padrão configurado na seção `if __name__ == "__main__":` faz o seguinte:

1.  Padroniza `input_bib/ieee_sample.bib`, `input_bib/scidirect_sample.bib`, `input_bib/mdpi_sample.bib` e salva em `standardized_bib/`.
2.  Remove duplicatas de `scidirect_standardized.bib` comparando com `ieee_standardized.bib`, salvando em `processed_bib/scidirect_unique_vs_ieee.bib`.
3.  Remove duplicatas de `mdpi_standardized.bib` comparando com `ieee_standardized.bib`, salvando em `processed_bib/mdpi_unique_vs_ieee.bib`.
4.  Converte `processed_bib/scidirect_unique_vs_ieee.bib` para `output_csv/scidirect_unique_vs_ieee.csv`.
5.  Converte `processed_bib/mdpi_unique_vs_ieee.bib` para `output_csv/mdpi_unique_vs_ieee.csv`.

Lembre-se de ajustar este fluxo conforme suas necessidades específicas.

