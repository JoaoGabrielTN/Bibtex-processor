#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
import csv
import os
import logging
import re # Importar regex para tratamento mais robusto do DOI

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Função de Normalização de DOI ---
def normalize_doi(doi_string):
    """Extrai o identificador DOI de uma string, lidando com URLs e convertendo para minúsculas."""
    if not doi_string:
        return ''
    doi_string = doi_string.strip().lower() # Normalize to lower case
    # Regex to find DOI: starts with 10., followed by numbers, then /, then characters
    # Handles optional URL prefixes like https://doi.org/
    match = re.search(r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', doi_string, re.IGNORECASE)
    if match:
        # Return the extracted DOI, already lowercased
        return match.group(1)
    # If no standard DOI pattern found, return the original cleaned string (lowercased) as fallback
    # Consider returning '' if only strict DOI format is desired.
    logging.warning(f"DOI string '{doi_string}' did not match standard pattern. Returning as is (lowercased).")
    return doi_string

# --- Função de Padronização ---
def standardize_bibtex_file(input_path, output_path):
    """
    Lê um arquivo BibTeX, padroniza suas entradas (incluindo DOI) e salva em um novo arquivo.
    """
    logging.info(f"Iniciando padronização do arquivo: {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as bibtex_file:
            # Use a custom parser to handle potential errors more gracefully if needed
            parser = BibTexParser(common_strings=True)
            parser.ignore_nonstandard_types = False
            parser.homogenize_fields = False # We handle homogenization
            # Add interpolation=False if encountering issues with % signs or similar
            # parser.interpolation = False
            bib_database = bibtexparser.load(bibtex_file, parser=parser)
    except FileNotFoundError:
        logging.error(f"Erro: Arquivo de entrada não encontrado em {input_path}")
        return
    except Exception as e:
        logging.error(f"Erro ao ler o arquivo BibTeX {input_path}: {e}")
        # Optionally re-raise or return an error indicator
        return

    standardized_db = BibDatabase()
    standardized_entries = []
    processed_ids = set() # Keep track of processed entry IDs

    for entry in bib_database.entries:
        try:
            original_id = entry.get('ID')
            original_entrytype = entry.get('ENTRYTYPE')

            if not original_id or not original_entrytype:
                logging.warning(f"Entrada sem ID ou ENTRYTYPE encontrada, pulando: {entry}")
                continue

            # Avoid processing the same ID multiple times if duplicates exist in input
            if original_id in processed_ids:
                logging.warning(f"ID de entrada duplicado '{original_id}' encontrado no arquivo {input_path}. Pulando ocorrência adicional.")
                continue
            processed_ids.add(original_id)

            # Padroniza campos para minúsculas, mas mantém ID e ENTRYTYPE originais
            standardized_entry_data = {k.lower(): v for k, v in entry.items() if k not in ['ID', 'ENTRYTYPE']}

            # --- Normalização do DOI ---
            raw_doi = standardized_entry_data.get('doi', '')
            standardized_entry_data['doi'] = normalize_doi(raw_doi) # Apply normalization

            # Garantir campos essenciais e tratar journal/booktitle
            essential_fields = ['doi', 'title', 'abstract', 'keywords', 'author', 'year', 'publisher', 'journal', 'booktitle', 'pages', 'volume', 'number']
            for field in essential_fields:
                if field not in standardized_entry_data:
                    standardized_entry_data[field] = '' # Add empty field if missing

            # Handle journal/booktitle consolidation
            if not standardized_entry_data.get('journal') and standardized_entry_data.get('booktitle'):
                standardized_entry_data['journal'] = standardized_entry_data['booktitle']
                # Optionally clear booktitle if journal is now populated
                # standardized_entry_data['booktitle'] = ''

            # Recriar a entrada final com ID/ENTRYTYPE originais e campos padronizados
            final_entry = {
                'ID': original_id,
                'ENTRYTYPE': original_entrytype
            }
            # Add only the essential fields we care about, ensuring order potentially
            for field in essential_fields:
                 final_entry[field] = standardized_entry_data.get(field, '')

            # Add any other fields that were present and lowercased, if desired
            # for key, value in standardized_entry_data.items():
            #     if key not in essential_fields and key not in ['id', 'entrytype']: # Avoid adding again
            #         final_entry[key] = value

            standardized_entries.append(final_entry)

        except Exception as e:
            entry_id_for_log = entry.get('ID', 'Desconhecido')
            logging.warning(f"Erro ao padronizar a entrada {entry_id_for_log} no arquivo {input_path}: {e}. Pulando entrada.")
            # Consider logging the full entry details for debugging if needed

    standardized_db.entries = standardized_entries

    try:
        writer = BibTexWriter()
        writer.indent = '  '     # Indentation for better readability
        writer.comma_first = False # Comma at the end
        # Ensure consistent field order if desired (optional)
        # writer.order_entries_by = ('ENTRYTYPE', 'ID')
        # writer.display_order = ('title', 'author', 'journal', 'year', ...) # Define explicit field order
        with open(output_path, 'w', encoding='utf-8') as bibtex_outfile:
            bibtex_outfile.write(writer.write(standardized_db))
        logging.info(f"Arquivo BibTeX padronizado salvo em: {output_path}")
    except Exception as e:
        logging.error(f"Erro ao salvar o arquivo BibTeX padronizado {output_path}: {e}")


# --- Função de Remoção de Duplicatas por DOI ---
def remove_duplicates_by_doi(file_x_path, file_y_path, output_path):
    """
    Remove entradas do arquivo X se o DOI (normalizado e em minúsculas) existir no arquivo Y.
    Assume que os arquivos de entrada já foram padronizados pela função standardize_bibtex_file.
    """
    logging.info(f"Iniciando remoção de duplicatas: {file_x_path} vs {file_y_path}")

    def load_bib(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as bibtex_file:
                parser = BibTexParser(common_strings=True)
                parser.ignore_nonstandard_types = False
                parser.homogenize_fields = False # Already standardized
                return bibtexparser.load(bibtex_file, parser=parser)
        except FileNotFoundError:
            logging.error(f"Erro: Arquivo não encontrado em {file_path}")
            return None
        except Exception as e:
            logging.error(f"Erro ao ler o arquivo BibTeX {file_path}: {e}")
            return None

    db_x = load_bib(file_x_path)
    db_y = load_bib(file_y_path)

    if db_x is None or db_y is None:
        logging.error("Não foi possível carregar um ou ambos os arquivos BibTeX. Abortando remoção de duplicatas.")
        return

    # Extrair DOIs do arquivo Y (já devem estar normalizados e em minúsculas pela padronização)
    dois_y = set()
    for entry in db_y.entries:
        # Get the already normalized DOI
        doi = entry.get('doi', '').strip() # Should be lowercase and just the ID
        if doi:
            dois_y.add(doi)
    logging.info(f"Encontrados {len(dois_y)} DOIs únicos no arquivo Y ({file_y_path}) para comparação.")

    # Filtrar entradas do arquivo X
    unique_entries_x = []
    removed_count = 0
    processed_ids_x = set() # Avoid duplicate processing within file X itself

    for entry in db_x.entries:
        entry_id = entry.get('ID')
        if entry_id in processed_ids_x:
             logging.warning(f"ID de entrada duplicado '{entry_id}' encontrado durante a filtragem de {file_x_path}. Pulando ocorrência adicional.")
             continue
        processed_ids_x.add(entry_id)

        # Get the already normalized DOI from file X entry
        doi_x = entry.get('doi', '').strip() # Should be lowercase and just the ID

        if not doi_x or doi_x not in dois_y:
            unique_entries_x.append(entry)
        else:
            removed_count += 1
            logging.info(f"Removendo entrada '{entry.get('ID')}' de X (DOI: {doi_x}) pois existe em Y.") # Changed to INFO for visibility

    logging.info(f"Removidas {removed_count} entradas duplicadas de {file_x_path} com base nos DOIs de {file_y_path}.")

    # Salvar resultado em novo arquivo BibTeX
    final_db = BibDatabase()
    final_db.entries = unique_entries_x
    try:
        writer = BibTexWriter()
        writer.indent = '  '
        writer.comma_first = False
        with open(output_path, 'w', encoding='utf-8') as bibtex_outfile:
            bibtex_outfile.write(writer.write(final_db))
        logging.info(f"Arquivo BibTeX sem duplicatas salvo em: {output_path}")
    except Exception as e:
        logging.error(f"Erro ao salvar o arquivo BibTeX resultante {output_path}: {e}")

# --- Função de Conversão para CSV ---
def convert_bibtex_to_csv(bibtex_path, csv_path):
    """
    Converte um arquivo BibTeX (padronizado) para CSV com colunas específicas.
    """
    logging.info(f"Iniciando conversão de BibTeX para CSV: {bibtex_path} -> {csv_path}")

    try:
        with open(bibtex_path, 'r', encoding='utf-8') as bibtex_file:
            parser = BibTexParser(common_strings=True)
            parser.ignore_nonstandard_types = False
            parser.homogenize_fields = False # Already standardized
            bib_database = bibtexparser.load(bibtex_file, parser=parser)
    except FileNotFoundError:
        logging.error(f"Erro: Arquivo BibTeX não encontrado em {bibtex_path}")
        return
    except Exception as e:
        logging.error(f"Erro ao ler o arquivo BibTeX {bibtex_path}: {e}")
        return

    # Definir cabeçalho do CSV
    # Make sure header names match the keys used below (case-sensitive for dict keys)
    csv_header = ['ID', 'doi', 'classification', 'title', 'abstract', 'keywords',
                  'Review', 'author', 'year', 'Publisher', 'journal', 'type title']

    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Use QUOTE_ALL for safety with complex fields like abstract/keywords
            writer = csv.DictWriter(csvfile, fieldnames=csv_header, quoting=csv.QUOTE_ALL)
            writer.writeheader()

            for entry in bib_database.entries:
                # Prepare row data using .get() for safety
                row_data = {
                    'ID': entry.get('ID', ''),
                    'doi': entry.get('doi', ''), # Already normalized
                    'classification': '', # Empty column as requested
                    'title': entry.get('title', ''),
                    'abstract': entry.get('abstract', ''),
                    'keywords': entry.get('keywords', ''),
                    'Review': '', # Empty column as requested
                    'author': entry.get('author', ''),
                    'year': entry.get('year', ''),
                    'Publisher': entry.get('publisher', ''), # Note: BibTeX field is 'publisher' (lowercase)
                    # Use 'journal' which might contain 'booktitle' from standardization
                    'journal': entry.get('journal', ''), # Already handled in standardization
                    'type title': entry.get('ENTRYTYPE', '').lower() # BibTeX entry type
                }

                # Clean potential problematic characters (like newlines) within fields for CSV
                for key, value in row_data.items():
                    if isinstance(value, str):
                        # Replace newlines and carriage returns with spaces, strip leading/trailing whitespace
                        row_data[key] = ' '.join(value.splitlines()).strip()

                writer.writerow(row_data)
        logging.info(f"Arquivo CSV gerado com sucesso em: {csv_path}")
    except Exception as e:
        logging.error(f"Erro ao escrever o arquivo CSV {csv_path}: {e}")

# --- Exemplo de Uso ---
if __name__ == "__main__":
    # Criar diretórios de exemplo se não existirem
    os.makedirs("input_bib", exist_ok=True)
    os.makedirs("standardized_bib", exist_ok=True)
    os.makedirs("processed_bib", exist_ok=True)
    os.makedirs("output_csv", exist_ok=True)

    # --- Arquivos de Exemplo (Crie estes arquivos ou substitua pelos seus) ---
    # Exemplo IEEE
    ieee_sample_content = """@INPROCEEDINGS{10911700,
      author={Vadher, Harshali Hemant and Aryan, Adla and Vamshi, Kuruva and Rajashekar, Ramojula and Ashish, Degavath and Arora, Gagan Deep},
      booktitle={2024 4th International Conference on Advancement in Electronics & Communication Engineering (AECE)},
      title={Unveiling the Potential of Machine Learning: Harnessing Machine Learning for Enhanced Coronary Heart Disease Detection and Intervention},
      year={2024},
      volume={},
      number={},
      pages={1073-1078},
      abstract={Coronary heart disease (CHD) remains a critical global health issue...},
      keywords={Support vector machines;Heart;Logistic regression;...;Predictive Modelling in Healthcare},
      doi={10.1109/AECE62803.2024.10911700},
      ISSN={},
      month={Nov},
    }
    @ARTICLE{example_article,
        author = {Doe, John and Smith, Jane},
        title = {Another Example Title},
        journal = {Journal of Examples},
        year = {2023},
        volume = {10},
        number = {2},
        pages = {1-10},
        doi = {10.1234/example.doi},
        abstract = {This is another abstract.},
        keywords = {example, testing, article}
    }"""
    with open("input_bib/ieee_sample.bib", "w", encoding="utf-8") as f:
        f.write(ieee_sample_content)

    # Exemplo ScienceDirect com DOI em URL
    scidirect_sample_content = """@article{SciDirect.123,
      author = {Scientist, Alice and Researcher, Bob},
      title = {ScienceDirect Example Paper},
      journal = {Elsevier Journal of Science},
      year = {2024},
      volume = {55},
      pages = {100-110},
      doi = {https://doi.org/10.1016/j.scij.2024.01.001},
      abstract = {Abstract from ScienceDirect.},
      keywords = {science, direct, research}
    }
    @article{duplicate_doi_test,
        author = {Tester, Duplicate},
        title = {Paper with Duplicate DOI},
        journal = {Journal of Duplicates},
        year = {2023},
        doi = {https://doi.org/10.1234/example.doi},
        abstract = {This abstract should be removed if DOI exists in the other file.},
        keywords = {duplicate, test}
    }"""
    with open("input_bib/scidirect_sample.bib", "w", encoding="utf-8") as f:
        f.write(scidirect_sample_content)

    # Exemplo MDPI
    mdpi_sample_content = """@Article{f16060891,
        AUTHOR = {Zhang, Jing and Wang, Cheng and Wang, Jinliang and Huang, Xiang and Zhou, Zilin and Zhou, Zetong and Cheng, Feng},
        TITLE = {Study on Forest Growing Stock Volume in Kunming City Considering the Relationship Between Stand Density and Allometry},
        JOURNAL = {Forests},
        VOLUME = {16},
        YEAR = {2025},
        NUMBER = {6},
        ARTICLE-NUMBER = {891},
        URL = {https://www.mdpi.com/1999-4907/16/6/891},
        ISSN = {1999-4907},
        ABSTRACT = {Forest growing stock volume (GSV) is a fundamental indicator...},
        DOI = {10.3390/f16060891}
    }"""
    with open("input_bib/mdpi_sample.bib", "w", encoding="utf-8") as f:
        f.write(mdpi_sample_content)

    # --- Caminhos dos Arquivos ---
    ieee_input = "input_bib/ieee_sample.bib"
    scidirect_input = "input_bib/scidirect_sample.bib"
    mdpi_input = "input_bib/mdpi_sample.bib"

    ieee_standardized = "standardized_bib/ieee_standardized.bib"
    scidirect_standardized = "standardized_bib/scidirect_standardized.bib"
    mdpi_standardized = "standardized_bib/mdpi_standardized.bib"

    # --- Execução do Fluxo ---

    # 1. Padronizar arquivos (inclui normalização de DOI)
    logging.info("--- Iniciando Etapa 1: Padronização ---")
    standardize_bibtex_file(ieee_input, ieee_standardized)
    standardize_bibtex_file(scidirect_input, scidirect_standardized)
    standardize_bibtex_file(mdpi_input, mdpi_standardized)

    # 2. Remover duplicatas
    # Exemplo: Remover de SciDirect (X) os DOIs presentes em IEEE (Y)
    logging.info("\n--- Iniciando Etapa 2a: Remoção de Duplicatas (SciDirect vs IEEE) ---")
    file_x_scidirect = scidirect_standardized
    file_y_ieee = ieee_standardized
    processed_scidirect_unique_vs_ieee = "processed_bib/scidirect_unique_vs_ieee.bib"
    remove_duplicates_by_doi(file_x_scidirect, file_y_ieee, processed_scidirect_unique_vs_ieee)

    # Exemplo: Remover de MDPI (X) os DOIs presentes em IEEE (Y)
    # Numa aplicação real, você poderia querer comparar MDPI contra IEEE E SciDirect único.
    # Para este exemplo, comparamos apenas contra IEEE.
    logging.info("\n--- Iniciando Etapa 2b: Remoção de Duplicatas (MDPI vs IEEE) ---")
    file_x_mdpi = mdpi_standardized
    # file_y_combined = # Logic to combine DOIs from ieee_standardized and processed_scidirect_unique_vs_ieee
    processed_mdpi_unique_vs_ieee = "processed_bib/mdpi_unique_vs_ieee.bib"
    remove_duplicates_by_doi(file_x_mdpi, file_y_ieee, processed_mdpi_unique_vs_ieee) # Using file_y_ieee for simplicity here

    # 3. Converter para CSV
    # Exemplo: Converter o arquivo SciDirect único (após remoção vs IEEE) para CSV
    logging.info("\n--- Iniciando Etapa 3a: Conversão para CSV (SciDirect Único vs IEEE) ---")
    csv_output_scidirect = "output_csv/scidirect_unique_vs_ieee.csv"
    convert_bibtex_to_csv(processed_scidirect_unique_vs_ieee, csv_output_scidirect)

    # Exemplo: Converter o arquivo MDPI único (após remoção vs IEEE) para CSV
    logging.info("\n--- Iniciando Etapa 3b: Conversão para CSV (MDPI Único vs IEEE) ---")
    csv_output_mdpi = "output_csv/mdpi_unique_vs_ieee.csv"
    convert_bibtex_to_csv(processed_mdpi_unique_vs_ieee, csv_output_mdpi)

    # --- Conclusão ---
    logging.info("\n--- Processamento Concluído ---")
    logging.info(f"Verifique os arquivos padronizados em: standardized_bib/")
    logging.info(f"Verifique os arquivos processados (sem duplicatas vs IEEE) em: processed_bib/")
    logging.info(f"Verifique os arquivos CSV gerados em: output_csv/")
    logging.info("NOTA: O fluxo remove duplicatas de SciDirect e MDPI comparando *separadamente* com IEEE.")
    logging.info("Para remover duplicatas de forma acumulada (ex: remover de MDPI o que existe em IEEE *ou* SciDirect)," )
    logging.info("você precisaria ajustar a Etapa 2 para carregar DOIs de múltiplos arquivos 'Y' ou processar sequencialmente.")

