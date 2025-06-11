#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     PYTHON CTRL+C SEARCH & PASTE TOOL                       ║
║                                                                              ║
║  Versão: 2.1.6 - CORREÇÃO COMPLETA QUEBRAS DE LINHA                        ║
║  Data: 2025-06-11                                                           ║
║  Autor: Sistema de Busca Inteligente                                        ║
║                                                                              ║
║  🎯 BUSCA INTELIGENTE DE CÓDIGO COM 6 ALGORITMOS DIFERENTES                 ║
║  📋 SISTEMA PASTE AUTOMÁTICO COM COORDENADAS SALVAS                         ║
║  🔄 BACKUP AUTOMÁTICO ANTES DE MODIFICAÇÕES                                 ║
║  🆕 CORREÇÃO: Cálculo preciso com quebras de linha diferentes               ║
║  🔧 CORREÇÃO: Ajuste automático de coordenadas no PASTE                     ║
║  🚨 CORREÇÃO: Mapeamento exato normalização → coordenadas originais         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import pyperclip
import sys
from datetime import datetime
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import shutil
import re
import codecs

# 🔧 Configuração de encoding para evitar problemas com caracteres especiais
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass  # Fallback para sistemas que não suportam reconfigure

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 CONFIGURAÇÕES GLOBAIS
# ═══════════════════════════════════════════════════════════════════════════════

PASTA_BASE = r"C:\Users"
EXTENSOES_NEGADAS = {".bak", ".bat"}

# 🆕 PADRÕES DE ARQUIVOS DE BACKUP PARA FILTRAR (v2.1.4)
PADROES_BACKUP = [
    r"\.backup_\d{8}_\d{6}$",  # arquivo.ext.backup_20250610_235341
    r"\.temp\.bak$",           # arquivo.ext.temp.bak
    r"~$",                     # arquivo.ext~
    r"\.orig$",                # arquivo.ext.orig
    r"\.old$",                 # arquivo.ext.old
]

LIMITE_SIMILARIDADE_TIPO5 = 10.0  # 🎯 AJUSTE AQUI: Similaridade mínima para TIPO 5 (0.0 a 100.0)

# 🆕 CONTROLE DE QUALIDADE DE RESULTADOS (v2.1.1)
LIMITE_PROBABILIDADE_MELHOR_RESULTADO = 80.0  # 🎯 AJUSTE AQUI: Só mostra como "melhor resultado" se >= 80% de probabilidade

# 🆕 SISTEMA DE SCORES POR TIPO DE BUSCA (v2.1.0)
SCORES_TIPOS = {
    1: 500,  # TIPO 1: 100% literal - máxima confiabilidade
    2: 400,  # TIPO 2: arquivo completo igual
    3: 300,  # TIPO 3: normalização de quebras (mais usado)
    4: 200,  # TIPO 4: com strip nas pontas
    5: 100,  # TIPO 5: base para probabilidade (+ similaridade%)
    6: 350   # 🆕 TIPO 6: ignorando U+000D completamente
}

# ═══════════════════════════════════════════════════════════════════════════════
# 🆕 ESTRUTURAS DE DADOS (v2.1.0)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResultadoBusca:
    """🆕 Estrutura padronizada para resultados de busca (v2.1.0)"""
    tipo: int
    nome_arquivo: str
    caminho_completo: str
    posicao_inicio: int
    posicao_fim: int
    tamanho_texto: int
    texto_original: str
    contexto_inicio: int
    contexto_fim: int
    contexto_texto: str
    similaridade: Optional[float] = None
    texto_encontrado: Optional[str] = None
    
    @property
    def score_confiabilidade(self) -> float:
        """🆕 Calcula score de confiabilidade baseado no tipo e similaridade"""
        score_base = SCORES_TIPOS.get(self.tipo, 0)
        if self.similaridade is not None:
            return score_base + self.similaridade
        return score_base

# 🆕 COLETOR GLOBAL DE RESULTADOS (v2.1.0)
resultados_globais: List[ResultadoBusca] = []

def limpar_resultados_globais():
    """🆕 Limpa a lista de resultados globais para nova busca"""
    global resultados_globais
    resultados_globais.clear()
    print("🧹 Resultados globais limpos para nova busca")

def adicionar_resultado_global(tipo: int, arquivo_info: Dict[str, Any]):
    """🆕 Adiciona resultado ao coletor global (v2.1.0)"""
    global resultados_globais
    
    resultado = ResultadoBusca(
        tipo=tipo,
        nome_arquivo=arquivo_info['nome'],
        caminho_completo=arquivo_info['caminho'],
        posicao_inicio=arquivo_info['inicio'],
        posicao_fim=arquivo_info['fim'],
        tamanho_texto=arquivo_info['tamanho'],
        texto_original=arquivo_info['texto_original'],
        contexto_inicio=arquivo_info['contexto_inicio'],
        contexto_fim=arquivo_info['contexto_fim'],
        contexto_texto=arquivo_info['contexto_texto'],
        similaridade=arquivo_info.get('similaridade'),
        texto_encontrado=arquivo_info.get('texto_encontrado')
    )
    
    resultados_globais.append(resultado)
    print(f"➕ Resultado TIPO{tipo} adicionado: {arquivo_info['nome']} (score: {resultado.score_confiabilidade:.1f})")

# ═══════════════════════════════════════════════════════════════════════════════
# 🆕 FUNÇÕES PARA TRATAMENTO DE U+000D (v2.1.2)
# ═══════════════════════════════════════════════════════════════════════════════

def detectar_problemas_carriage_return(texto):
    """🆕 Detecta e reporta problemas com U+000D no texto (v2.1.2)"""
    count_cr = texto.count('\r')
    count_crlf = texto.count('\r\n')
    count_cr_isolado = count_cr - count_crlf
    
    problemas = []
    if count_cr_isolado > 0:
        problemas.append(f"⚠️ {count_cr_isolado} carriage returns isolados (\\r sem \\n)")
    if count_crlf > 0:
        problemas.append(f"📝 {count_crlf} sequências CRLF (\\r\\n)")
    
    if problemas:
        print(f"🔍 ANÁLISE DE QUEBRAS DE LINHA:")
        for problema in problemas:
            print(f"   {problema}")
    
    return count_cr_isolado > 0

def limpar_carriage_returns(texto):
    """🆕 Remove todos os \\r do texto de forma inteligente (v2.1.2)"""
    # Primeiro converte \r\n para \n
    texto_limpo = texto.replace('\r\n', '\n')
    # Depois remove qualquer \r restante (isolado)
    texto_limpo = texto_limpo.replace('\r', '')
    return texto_limpo

def normalizar_quebras_avancado(texto):
    """🆕 Normalização avançada que trata todos os tipos de quebras (v2.1.2)"""
    # Remove todos os \r (tanto isolados quanto em \r\n)
    texto_sem_cr = limpar_carriage_returns(texto)
    return texto_sem_cr

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 FUNÇÕES AUXILIARES ATUALIZADAS
# ═══════════════════════════════════════════════════════════════════════════════

def eh_arquivo_backup(nome_arquivo):
    """🆕 Verifica se o arquivo é um backup usando padrões regex (v2.1.4)"""
    for padrao in PADROES_BACKUP:
        if re.search(padrao, nome_arquivo):
            return True
    return False

def detectar_bom_e_encoding(caminho_arquivo: str) -> Dict[str, Any]:
    """🆕 Detecta BOM e encoding automaticamente"""
    try:
        with open(caminho_arquivo, 'rb') as f:
            raw_bytes = f.read(4)
        
        if raw_bytes.startswith(codecs.BOM_UTF8):
            return {
                'encoding': 'utf-8-sig',
                'bom_size': len(codecs.BOM_UTF8),
                'has_bom': True,
                'detected': 'UTF-8 with BOM'
            }
        elif raw_bytes.startswith(codecs.BOM_UTF16_LE):
            return {
                'encoding': 'utf-16-le',
                'bom_size': len(codecs.BOM_UTF16_LE),
                'has_bom': True,
                'detected': 'UTF-16 LE with BOM'
            }
        else:
            try:
                with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                    f.read(100)
                return {
                    'encoding': 'utf-8',
                    'bom_size': 0,
                    'has_bom': False,
                    'detected': 'UTF-8 without BOM'
                }
            except UnicodeDecodeError:
                return {
                    'encoding': 'latin-1',
                    'bom_size': 0,
                    'has_bom': False,
                    'detected': 'Latin-1 (fallback)'
                }
    except Exception as e:
        return {
            'encoding': 'utf-8',
            'bom_size': 0,
            'has_bom': False,
            'detected': 'UTF-8 (error fallback)'
        }

def ler_arquivo_corrigido_bom(caminho):
    """🔧 Versão corrigida que remove BOM corretamente"""
    info_encoding = detectar_bom_e_encoding(caminho)
    
    try:
        # Se tem BOM, usa utf-8-sig que remove automaticamente
        if info_encoding['has_bom'] and 'utf-8' in info_encoding['detected'].lower():
            with open(caminho, 'r', encoding='utf-8-sig', errors='replace') as f:
                conteudo = f.read()
            print(f"   🔧 BOM UTF-8 removido automaticamente ({info_encoding['bom_size']} bytes)")
        else:
            # Sem BOM ou outro encoding
            with open(caminho, 'r', encoding=info_encoding['encoding'], errors='replace') as f:
                conteudo = f.read()
            if info_encoding['has_bom']:
                print(f"   🔖 BOM detectado: {info_encoding['bom_size']} bytes")
        
        return conteudo
        
    except Exception as e:
        print(f"❌ Erro ao ler {caminho}: {e}")
        # Fallback
        try:
            with open(caminho, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except:
            return ""

def ler_arquivo_com_bom_detection(caminho: str) -> Tuple[str, Dict[str, Any]]:
    """🆕 Lê arquivo com detecção automática de BOM"""
    info_encoding = detectar_bom_e_encoding(caminho)
    
    try:
        # 🚨 CORREÇÃO CRÍTICA: Usa utf-8-sig para remover BOM automaticamente
        if info_encoding['has_bom'] and 'utf-8' in info_encoding['detected'].lower():
            with open(caminho, 'r', encoding='utf-8-sig', errors='replace') as f:
                conteudo = f.read()
            print(f"   🔧 BOM UTF-8 removido automaticamente ({info_encoding['bom_size']} bytes)")
        else:
            with open(caminho, 'r', encoding=info_encoding['encoding'], errors='replace') as f:
                conteudo = f.read()
            if info_encoding['has_bom']:
                print(f"   🔖 BOM detectado: {info_encoding['bom_size']} bytes")
        
        return conteudo, info_encoding
        
    except Exception as e:
        print(f"❌ Erro ao ler {caminho}: {e}")
        try:
            with open(caminho, 'r', encoding='utf-8', errors='replace') as f:
                return f.read(), info_encoding
        except:
            return "", info_encoding

def mapear_posicao_normalizada_para_original_melhorado(
    conteudo_original: str, 
    conteudo_normalizado: str, 
    posicao_normalizada: int
) -> Optional[int]:
    """🆕 Mapeamento preciso que conta diferenças de quebras"""
    if posicao_normalizada >= len(conteudo_normalizado):
        return None
    
    chars_contados = 0
    pos_original = 0
    
    while chars_contados < posicao_normalizada and pos_original < len(conteudo_original):
        char_original = conteudo_original[pos_original]
        
        if char_original == '\r':
            if pos_original + 1 < len(conteudo_original) and conteudo_original[pos_original + 1] == '\n':
                # CRLF: pula 2 chars no original, conta 1 no normalizado
                pos_original += 2
                chars_contados += 1
            else:
                # CR isolado: pula 1 char no original, conta 1 no normalizado
                pos_original += 1
                chars_contados += 1
        else:
            # Char normal: avança ambos
            pos_original += 1
            chars_contados += 1
    
    return pos_original

def obter_texto_copiado():
    try:
        texto = pyperclip.paste()
        return texto if texto else ""
    except:
        return ""

def ler_arquivo(caminho):
    """🔧 Função corrigida que usa o método corrigido para BOM"""
    return ler_arquivo_corrigido_bom(caminho)

def mostrar_debug_texto(texto, nome):
    """🆕 Mostra informações detalhadas do texto incluindo análise de \\r (v2.1.2)"""
    print(f"📋 {nome}:")
    print(f"   Tamanho: {len(texto)} caracteres")
    print(f"   Repr: {repr(texto[:100])}")
    print(f"   Hex: {' '.join(f'{ord(c):02x}' for c in texto[:20])}")
    
    # 🆕 ANÁLISE ESPECÍFICA DE CARRIAGE RETURNS
    detectar_problemas_carriage_return(texto)

# ═══════════════════════════════════════════════════════════════════════════════
# 🚨 FUNÇÃO CORRIGIDA PARA CÁLCULO PRECISO DE POSIÇÕES (CORREÇÃO COMPLETA)
# ═══════════════════════════════════════════════════════════════════════════════

def calcular_posicoes_precisas(conteudo_original: str, texto_procurado: str, debug_arquivo: str = "", caminho_arquivo: str = "") -> Optional[Dict[str, int]]:
    """🔧 Versão CORRIGIDA v2.1.6 - Mapeamento preciso com quebras de linha diferentes"""
    if not texto_procurado or not conteudo_original:
        return None
    
    # 🚨 CRÍTICO: Detecta se arquivo original tinha BOM
    offset_bom = 0
    if caminho_arquivo and os.path.exists(caminho_arquivo):
        info_encoding = detectar_bom_e_encoding(caminho_arquivo)
        if info_encoding['has_bom'] and 'utf-8' in info_encoding['detected'].lower():
            offset_bom = info_encoding['bom_size']
            if debug_arquivo:
                print(f"🔖 BOM detectado: ajustando posições em +{offset_bom} bytes")
    
    if debug_arquivo:
        print(f"🔍 Iniciando busca precisa em {debug_arquivo} (offset BOM: {offset_bom})")
        print(f"   📊 Conteúdo: {len(conteudo_original)} chars")
        print(f"   📊 Procurado: {len(texto_procurado)} chars")
    
    # ESTRATÉGIA 1: BUSCA DIRETA
    try:
        posicao_direta = conteudo_original.find(texto_procurado)
        if posicao_direta != -1:
            if debug_arquivo:
                print(f"✅ ESTRATÉGIA 1: Busca direta OK (pos: {posicao_direta} + BOM: {offset_bom})")
            return {
                'inicio': posicao_direta + offset_bom,  # 🚨 AJUSTE BOM
                'fim': posicao_direta + len(texto_procurado) + offset_bom  # 🚨 AJUSTE BOM
            }
    except Exception as e:
        if debug_arquivo:
            print(f"❌ ESTRATÉGIA 1: Erro na busca direta: {e}")
    
    # ESTRATÉGIA 2: NORMALIZAÇÃO DE QUEBRAS (MELHORADA v2.1.6)
    try:
        texto_norm = texto_procurado.replace('\r\n', '\n').replace('\r', '\n')
        conteudo_norm = conteudo_original.replace('\r\n', '\n').replace('\r', '\n')
        
        posicao_norm = conteudo_norm.find(texto_norm)
        if posicao_norm != -1:
            if debug_arquivo:
                print(f"🔧 ESTRATÉGIA 2: Normalização OK (pos normalizada: {posicao_norm})")
            
            # 🆕 MAPEAMENTO PRECISO: Posição normalizada → original
            contador = 0
            pos_real = 0
            
            for i, char in enumerate(conteudo_original):
                if contador >= posicao_norm:
                    pos_real = i
                    break
                
                if char == '\r':
                    if i + 1 < len(conteudo_original) and conteudo_original[i + 1] == '\n':
                        # CRLF: pula \r (será contado como \n no próximo)
                        continue
                    else:
                        # CR isolado: conta como 1
                        contador += 1
                else:
                    contador += 1
            
            # 🆕 CALCULA FIM BASEADO NO TAMANHO ORIGINAL DO TEXTO
            chars_mapeados = 0
            fim_real = pos_real
            
            for i in range(pos_real, len(conteudo_original)):
                if chars_mapeados >= len(texto_procurado):
                    break
                fim_real = i + 1
                chars_mapeados += 1
            
            if debug_arquivo:
                print(f"   📍 Pos real mapeada: {pos_real} até {fim_real}")
                print(f"   🔧 Ajuste BOM: +{offset_bom}")
                
                # Validação do mapeamento
                texto_extraido = conteudo_original[pos_real:fim_real]
                texto_extraido_norm = texto_extraido.replace('\r\n', '\n').replace('\r', '\n')
                if texto_extraido_norm == texto_norm:
                    print(f"   ✅ Mapeamento validado: textos idênticos após normalização")
                else:
                    print(f"   ⚠️ Mapeamento com diferenças pequenas")
            
            return {
                'inicio': pos_real + offset_bom,  # 🚨 AJUSTE BOM
                'fim': fim_real + offset_bom      # 🚨 AJUSTE BOM
            }
    except Exception as e:
        if debug_arquivo:
            print(f"❌ ESTRATÉGIA 2: Erro na normalização: {e}")
    
    # ESTRATÉGIA 3: BUSCA POR ÂNCORAS (com ajuste BOM)
    try:
        linhas = [l.strip() for l in texto_procurado.split('\n') if l.strip()]
        if len(linhas) >= 2:
            primeira = linhas[0]
            ultima = linhas[-1]
            
            pos_primeira = conteudo_original.find(primeira)
            if pos_primeira != -1:
                pos_ultima = conteudo_original.find(ultima, pos_primeira + len(primeira))
                if pos_ultima != -1:
                    inicio = max(0, pos_primeira - 50)
                    fim = min(len(conteudo_original), pos_ultima + len(ultima) + 50)
                    regiao = conteudo_original[inicio:fim]
                    
                    pos_regiao = regiao.find(texto_procurado)
                    if pos_regiao != -1:
                        if debug_arquivo:
                            print(f"⚓ ESTRATÉGIA 3: Âncoras OK (+ BOM: {offset_bom})")
                        return {
                            'inicio': inicio + pos_regiao + offset_bom,  # 🚨 AJUSTE BOM
                            'fim': inicio + pos_regiao + len(texto_procurado) + offset_bom  # 🚨 AJUSTE BOM
                        }
    except Exception as e:
        if debug_arquivo:
            print(f"❌ ESTRATÉGIA 3: Erro nas âncoras: {e}")
    
    # ESTRATÉGIA 4: STRIP
    try:
        texto_strip = texto_procurado.strip()
        if len(texto_strip) != len(texto_procurado):
            pos_strip = conteudo_original.find(texto_strip)
            if pos_strip != -1:
                if debug_arquivo:
                    print(f"✂️ ESTRATÉGIA 4: Strip OK (+ BOM: {offset_bom})")
                return {
                    'inicio': pos_strip + offset_bom,  # 🚨 AJUSTE BOM
                    'fim': pos_strip + len(texto_strip) + offset_bom  # 🚨 AJUSTE BOM
                }
    except Exception as e:
        if debug_arquivo:
            print(f"❌ ESTRATÉGIA 4: Erro no strip: {e}")
    
    if debug_arquivo:
        print(f"❌ TODAS ESTRATÉGIAS FALHARAM para {debug_arquivo}")
    
    return None

def validar_posicoes_com_bom(conteudo_original: str, posicoes: Dict[str, int], texto_esperado: str, caminho_arquivo: str, debug_arquivo: str = "") -> bool:
    """🆕 Valida posições considerando offset BOM"""
    # Detecta offset BOM
    offset_bom = 0
    if caminho_arquivo and os.path.exists(caminho_arquivo):
        info_encoding = detectar_bom_e_encoding(caminho_arquivo)
        if info_encoding['has_bom'] and 'utf-8' in info_encoding['detected'].lower():
            offset_bom = info_encoding['bom_size']
    
    # Remove offset BOM para validar no conteúdo sem BOM
    inicio = posicoes['inicio'] - offset_bom
    fim = posicoes['fim'] - offset_bom
    
    # Verificações básicas
    if inicio < 0 or fim > len(conteudo_original) or inicio >= fim:
        if debug_arquivo:
            print(f"❌ Validação FALHOU para {debug_arquivo}: limites inválidos (ajustados para BOM: -{offset_bom})")
        return False
    
    # Extrai o texto nas posições calculadas
    texto_extraido = conteudo_original[inicio:fim]
    
    # 🔍 VALIDAÇÃO RIGOROSA
    if texto_extraido == texto_esperado:
        if debug_arquivo:
            print(f"✅ Validação OK para {debug_arquivo}: textos idênticos (com ajuste BOM: +{offset_bom})")
        return True
    
    # 🔧 VALIDAÇÃO FLEXÍVEL PARA QUEBRAS DE LINHA
    texto_extraido_norm = texto_extraido.replace('\r\n', '\n')
    texto_esperado_norm = texto_esperado.replace('\r\n', '\n')
    
    if texto_extraido_norm == texto_esperado_norm:
        if debug_arquivo:
            print(f"✅ Validação OK para {debug_arquivo}: textos idênticos após normalização (BOM: +{offset_bom})")
        return True
    
    # 🆕 VALIDAÇÃO FLEXÍVEL PARA U+000D
    texto_extraido_sem_cr = limpar_carriage_returns(texto_extraido)
    texto_esperado_sem_cr = limpar_carriage_returns(texto_esperado)
    
    if texto_extraido_sem_cr == texto_esperado_sem_cr:
        if debug_arquivo:
            print(f"✅ Validação OK para {debug_arquivo}: textos idênticos após remover \\r (BOM: +{offset_bom})")
        return True
    
    if debug_arquivo:
        print(f"❌ Validação FALHOU para {debug_arquivo}: textos diferentes (mesmo com ajuste BOM: +{offset_bom})")
        print(f"   📝 Extraído: {repr(texto_extraido[:50])}")
        print(f"   📝 Esperado: {repr(texto_esperado[:50])}")
    
    return False

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 FUNÇÕES DE BUSCA ATUALIZADAS
# ═══════════════════════════════════════════════════════════════════════════════

def tipo1_comparacao_literal(texto_copiado):
    """TIPO 1: Comparação 100% literal - NADA é removido"""
    print("🔍 TIPO 1: COMPARAÇÃO 100% LITERAL (v2.1.6 - CORREÇÃO COMPLETA)")
    print("Regra: texto_copiado in conteudo_arquivo")
    
    for raiz, _, arquivos in os.walk(PASTA_BASE):
        for arquivo in arquivos:
            ext = os.path.splitext(arquivo)[1].lower()
            if ext in EXTENSOES_NEGADAS or eh_arquivo_backup(arquivo):
                continue
                
            caminho_arquivo = os.path.join(raiz, arquivo)
            conteudo = ler_arquivo(caminho_arquivo)
            
            if texto_copiado in conteudo:
                print(f"✅ OK - {arquivo}")
                
                # 🚨 PASSA CAMINHO PARA CORREÇÃO BOM
                posicoes = calcular_posicoes_precisas(conteudo, texto_copiado, arquivo, caminho_arquivo)
                if not posicoes:
                    print(f"❌ Erro ao calcular posições para {arquivo}")
                    continue
                
                if not validar_posicoes_com_bom(conteudo, posicoes, texto_copiado, caminho_arquivo, arquivo):
                    print(f"❌ Validação falhou para {arquivo}")
                    continue
                
                contexto_inicio = max(0, posicoes['inicio'] - 50)
                contexto_fim = min(len(conteudo) + 3, posicoes['fim'] + 50)  # +3 para BOM
                
                arquivo_info = {
                    'nome': arquivo,
                    'caminho': caminho_arquivo,
                    'inicio': posicoes['inicio'],
                    'fim': posicoes['fim'],
                    'tamanho': len(texto_copiado),
                    'texto_original': texto_copiado,
                    'contexto_inicio': contexto_inicio,
                    'contexto_fim': contexto_fim,
                    'contexto_texto': conteudo[max(0, contexto_inicio-3):contexto_fim-3]  # Ajuste contexto
                }
                
                adicionar_resultado_global(1, arquivo_info)
                return
    
    print("❌ FAIL")

def tipo2_comparacao_arquivo_completo(texto_copiado):
    """TIPO 2: Arquivo completo deve ser igual ao texto copiado"""
    print("🔍 TIPO 2: ARQUIVO COMPLETO IGUAL AO TEXTO")
    print("Regra: texto_copiado == conteudo_arquivo")
    
    for raiz, _, arquivos in os.walk(PASTA_BASE):
        for arquivo in arquivos:
            ext = os.path.splitext(arquivo)[1].lower()
            if ext in EXTENSOES_NEGADAS or eh_arquivo_backup(arquivo):
                continue
                
            caminho_arquivo = os.path.join(raiz, arquivo)
            conteudo = ler_arquivo(caminho_arquivo)
            
            if texto_copiado == conteudo:
                print(f"✅ OK - {arquivo}")
                
                arquivo_info = {
                    'nome': arquivo,
                    'caminho': caminho_arquivo,
                    'inicio': 0,
                    'fim': len(conteudo),
                    'tamanho': len(texto_copiado),
                    'texto_original': texto_copiado,
                    'contexto_inicio': 0,
                    'contexto_fim': len(conteudo),
                    'contexto_texto': conteudo
                }
                
                adicionar_resultado_global(2, arquivo_info)
                return
    
    print("❌ FAIL")

def tipo3_comparacao_quebras_normalizadas(texto_copiado):
    """🔧 TIPO 3: Normaliza quebras de linha \\r\\n para \\n"""
    print("🔍 TIPO 3: QUEBRAS DE LINHA NORMALIZADAS (v2.1.6 - CORREÇÃO COMPLETA)")
    print("Regra: normaliza \\r\\n para \\n, depois texto_copiado in conteudo")
    
    texto_normalizado = texto_copiado.replace('\r\n', '\n')
    arquivos_encontrados = 0
    
    for raiz, _, arquivos in os.walk(PASTA_BASE):
        for arquivo in arquivos:
            ext = os.path.splitext(arquivo)[1].lower()
            if ext in EXTENSOES_NEGADAS or eh_arquivo_backup(arquivo):
                continue
                
            caminho_arquivo = os.path.join(raiz, arquivo)
            conteudo_original = ler_arquivo(caminho_arquivo)
            conteudo_normalizado = conteudo_original.replace('\r\n', '\n')
            
            if texto_normalizado in conteudo_normalizado:
                print(f"🔍 Calculando posições precisas para {arquivo}...")
                
                # 🚨 PASSA CAMINHO PARA CORREÇÃO BOM
                posicoes = calcular_posicoes_precisas(conteudo_original, texto_copiado, arquivo, caminho_arquivo)
                if not posicoes:
                    print(f"❌ Erro ao calcular posições para {arquivo}")
                    continue
                
                if not validar_posicoes_com_bom(conteudo_original, posicoes, texto_copiado, caminho_arquivo, arquivo):
                    print(f"❌ Validação falhou para {arquivo}")
                    continue
                
                contexto_inicio = max(0, posicoes['inicio'] - 50)
                contexto_fim = min(len(conteudo_original) + 3, posicoes['fim'] + 50)  # +3 para BOM
                contexto_texto = conteudo_original[max(0, contexto_inicio-3):contexto_fim-3]  # Ajuste contexto
                
                arquivo_info = {
                    'nome': arquivo,
                    'caminho': caminho_arquivo,
                    'inicio': posicoes['inicio'],
                    'fim': posicoes['fim'],
                    'tamanho': len(texto_copiado),
                    'texto_original': texto_copiado,
                    'contexto_inicio': contexto_inicio,
                    'contexto_fim': contexto_fim,
                    'contexto_texto': contexto_texto
                }
                
                adicionar_resultado_global(3, arquivo_info)
                arquivos_encontrados += 1
                print(f"✅ ENCONTRADO - {arquivo}")
    
    if arquivos_encontrados > 0:
        print(f"\n🎯 RESUMO TIPO3: Texto encontrado em {arquivos_encontrados} arquivo(s)")
    else:
        print("❌ FAIL")

def tipo4_comparacao_strip_aplicado(texto_copiado):
    """TIPO 4: Remove espaços do início e fim (.strip())"""
    print("🔍 TIPO 4: COM STRIP NAS PONTAS (v2.1.6 - CORREÇÃO COMPLETA)")
    print("Regra: aplica .strip() em ambos, depois texto_copiado in conteudo")
    
    texto_stripped = texto_copiado.strip()
    
    for raiz, _, arquivos in os.walk(PASTA_BASE):
        for arquivo in arquivos:
            ext = os.path.splitext(arquivo)[1].lower()
            if ext in EXTENSOES_NEGADAS or eh_arquivo_backup(arquivo):
                continue
                
            caminho_arquivo = os.path.join(raiz, arquivo)
            conteudo = ler_arquivo(caminho_arquivo)
            conteudo_stripped = conteudo.strip()
            
            if texto_stripped in conteudo_stripped:
                print(f"✅ OK - {arquivo}")
                
                # 🚨 PASSA CAMINHO PARA CORREÇÃO BOM
                posicoes = calcular_posicoes_precisas(conteudo, texto_copiado, arquivo, caminho_arquivo)
                if not posicoes:
                    posicoes_stripped = calcular_posicoes_precisas(conteudo, texto_stripped, arquivo, caminho_arquivo)
                    if posicoes_stripped:
                        posicoes = posicoes_stripped
                    else:
                        print(f"❌ Erro ao calcular posições para {arquivo}")
                        continue
                
                contexto_inicio = max(0, posicoes['inicio'] - 50)
                contexto_fim = min(len(conteudo) + 3, posicoes['fim'] + 50)  # +3 para BOM
                
                arquivo_info = {
                    'nome': arquivo,
                    'caminho': caminho_arquivo,
                    'inicio': posicoes['inicio'],
                    'fim': posicoes['fim'],
                    'tamanho': len(texto_copiado),
                    'texto_original': texto_copiado,
                    'contexto_inicio': contexto_inicio,
                    'contexto_fim': contexto_fim,
                    'contexto_texto': conteudo[max(0, contexto_inicio-3):contexto_fim-3]  # Ajuste contexto
                }
                
                adicionar_resultado_global(4, arquivo_info)
                return
    
    print("❌ FAIL")

def calcular_similaridade_melhorada(texto1, texto2):
    """
    🔧 ALGORITMO OTIMIZADO: Calcula similaridade mais precisa
    """
    def normalizar_texto(texto):
        linhas = []
        for linha in texto.split('\n'):
            linha_limpa = linha.strip()
            if linha_limpa:
                linhas.append(linha_limpa)
        return '\n'.join(linhas)
    
    texto1_norm = normalizar_texto(texto1)
    texto2_norm = normalizar_texto(texto2)
    
    if texto1_norm == texto2_norm:
        return 100.0
    if not texto1_norm or not texto2_norm:
        return 0.0
    
    # 🎯 ALGORITMO MELHORADO: Combina múltiplas métricas
    
    # 1. Similaridade de caracteres
    chars1 = set(texto1_norm.lower())
    chars2 = set(texto2_norm.lower())
    if chars1.union(chars2):
        sim_chars = len(chars1.intersection(chars2)) / len(chars1.union(chars2))
    else:
        sim_chars = 0
    
    # 2. Similaridade de palavras
    palavras1 = set(texto1_norm.lower().split())
    palavras2 = set(texto2_norm.lower().split())
    if palavras1.union(palavras2):
        sim_palavras = len(palavras1.intersection(palavras2)) / len(palavras1.union(palavras2))
    else:
        sim_palavras = 0
    
    # 3. Similaridade de tamanho
    tam_min = min(len(texto1_norm), len(texto2_norm))
    tam_max = max(len(texto1_norm), len(texto2_norm))
    sim_tamanho = tam_min / tam_max if tam_max > 0 else 0
    
    # 4. Bonus substring
    texto1_lower = texto1_norm.lower()
    texto2_lower = texto2_norm.lower()
    if texto1_lower in texto2_lower or texto2_lower in texto1_lower:
        bonus_substring = 0.3
    else:
        bonus_substring = 0
    
    # 🏆 FÓRMULA FINAL
    similaridade_final = (
        sim_chars * 0.3 +
        sim_palavras * 0.4 +
        sim_tamanho * 0.2 +
        bonus_substring
    ) * 100
    
    return min(100.0, similaridade_final)

def extrair_ancoras(texto):
    """🆕 Extrai âncoras TRIPLAS para busca por probabilidade (inicial, meio, final) - v2.1.1"""
    linhas = [linha.strip() for linha in texto.split('\n') if linha.strip()]
    
    if not linhas:
        return None, None, None
    
    if len(linhas) == 1:
        return linhas[0], linhas[0], linhas[0]
    
    if len(linhas) == 2:
        return linhas[0], linhas[0], linhas[1]  # inicial, inicial como meio, final
    
    # 🎯 CALCULA POSIÇÃO DO MEIO (mais inteligente)
    indice_meio = len(linhas) // 2
    
    return linhas[0], linhas[indice_meio], linhas[-1]

def tipo5_busca_por_probabilidade(texto_copiado, limite_similaridade=90.0):
    """🆕 TIPO 5: Busca por probabilidade com CORREÇÃO COMPLETA v2.1.6"""
    print("🔍 TIPO 5: BUSCA POR PROBABILIDADE COM CORREÇÃO COMPLETA")
    print(f"Regra: Âncoras inicial/final + análise TIPO3 na linha do meio, similaridade >= {limite_similaridade}%")
    
    ancora_inicial, ancora_meio, ancora_final = extrair_ancoras(texto_copiado)
    
    if not ancora_inicial:
        print("❌ ERRO: Não foi possível extrair âncoras do texto copiado")
        return
    
    print(f"🎯 ÂNCORAS EXTRAÍDAS:")
    print(f"   📍 Inicial: {repr(ancora_inicial[:50])}")
    print(f"   📍 Meio (TIPO3): {repr(ancora_meio[:50])}")
    print(f"   📍 Final: {repr(ancora_final[:50])}")
    
    # 🆕 PREPARA LINHA DO MEIO PARA ANÁLISE TIPO3
    linha_meio_normalizada = ancora_meio.replace('\r\n', '\n')
    print(f"🔬 ESTRATÉGIA MATEMÁTICA: Aplicando precisão TIPO3 na linha do meio")
    
    arquivos_encontrados = 0
    
    for raiz, _, arquivos in os.walk(PASTA_BASE):
        for arquivo in arquivos:
            ext = os.path.splitext(arquivo)[1].lower()
            if ext in EXTENSOES_NEGADAS or eh_arquivo_backup(arquivo):
                continue
                
            caminho_arquivo = os.path.join(raiz, arquivo)
            conteudo_original = ler_arquivo(caminho_arquivo)
            
            # 1. 🔍 BUSCA ÂNCORA INICIAL (primeira validação)
            pos_inicial = conteudo_original.find(ancora_inicial)
            if pos_inicial == -1:
                continue  # Âncora inicial não encontrada
            
            # 2. 🔍 BUSCA ÂNCORA FINAL (segunda validação)
            pos_busca_final = pos_inicial + len(ancora_inicial)
            pos_final_ancora = conteudo_original.find(ancora_final, pos_busca_final)
            
            if pos_final_ancora == -1:
                if ancora_inicial == ancora_final:
                    pos_final_ancora = pos_inicial
                else:
                    continue
            
            # 3. 🆕 ANÁLISE MATEMÁTICA HÍBRIDA: TIPO3 na linha do meio
            score_matematico = 0
            bonus_tipo3_meio = 0
            bonus_ancora_meio = 0
            bonus_precisao = 0
            
            # Aplica TIPO3 especificamente na linha do meio
            conteudo_normalizado = conteudo_original.replace('\r\n', '\n')
            
            if linha_meio_normalizada in conteudo_normalizado:
                # 🏆 TIPO3 na linha do meio ENCONTRADO!
                pos_meio_tipo3 = conteudo_normalizado.find(linha_meio_normalizada)
                
                # Verifica se a linha do meio está dentro da região das âncoras
                pos_inicial_normalizada = conteudo_normalizado.find(ancora_inicial.replace('\r\n', '\n'))
                pos_final_normalizada = conteudo_normalizado.find(ancora_final.replace('\r\n', '\n'), pos_inicial_normalizada + len(ancora_inicial))
                
                if pos_inicial_normalizada <= pos_meio_tipo3 <= pos_final_normalizada:
                    bonus_tipo3_meio = 35.0  # 🎯 BONUS MATEMÁTICO: +35% por TIPO3 válido no meio
                    score_matematico += bonus_tipo3_meio
                    print(f"🧮 {arquivo}: TIPO3 na linha do meio CONFIRMADO! (+{bonus_tipo3_meio:.1f}% bonus)")
                    
                    # 🆕 BONUS EXTRA: Se consegue validar posições precisas
                    posicoes_teste = calcular_posicoes_precisas(conteudo_original, texto_copiado, "", caminho_arquivo)
                    if posicoes_teste:
                        bonus_precisao = 25.0  # Bonus por posições válidas
                        score_matematico += bonus_precisao
                        print(f"🎯 {arquivo}: Posições precisas validadas (+{bonus_precisao:.1f}% bonus de precisão)")
                else:
                    print(f"⚠️ {arquivo}: TIPO3 linha do meio encontrada, mas fora da região das âncoras")
            else:
                print(f"📊 {arquivo}: Linha do meio não passa no teste TIPO3")
            
            # 4. 🎯 BUSCA ÂNCORA DO MEIO TRADICIONAL (validação adicional)
            if ancora_meio != ancora_inicial and ancora_meio != ancora_final:
                pos_busca_meio_inicio = pos_inicial + len(ancora_inicial)
                pos_busca_meio_fim = pos_final_ancora
                trecho_busca_meio = conteudo_original[pos_busca_meio_inicio:pos_busca_meio_fim + len(ancora_final)]
                pos_meio_relativa = trecho_busca_meio.find(ancora_meio)
                
                if pos_meio_relativa != -1:
                    bonus_ancora_meio = 10.0  # Bonus menor por âncora tradicional
                    score_matematico += bonus_ancora_meio
                    print(f"✅ {arquivo}: Âncora do meio tradicional encontrada (+{bonus_ancora_meio:.1f}% bonus)")
                else:
                    print(f"⚠️ {arquivo}: Âncora do meio tradicional não localizada")
            else:
                # 🆕 CASO ESPECIAL: Âncoras inicial/final iguais (comentários repetitivos)
                if ancora_inicial == ancora_final:
                    # Dá bonus se a linha do meio é diferente e específica
                    if ancora_meio != ancora_inicial and len(ancora_meio.strip()) > 10:
                        bonus_ancora_meio = 20.0  # Bonus por linha do meio específica
                        score_matematico += bonus_ancora_meio
                        print(f"🔥 {arquivo}: Linha do meio específica em bloco com bordas iguais (+{bonus_ancora_meio:.1f}% bonus)")
                    else:
                        print(f"📝 {arquivo}: Âncoras inicial/final iguais (bordas de comentário)")
                else:
                    print(f"📝 {arquivo}: Âncora do meio igual às bordas (texto pequeno)")
            
            # 5. 🎯 CALCULA POSIÇÕES E SIMILARIDADE BASE
            inicio_trecho = pos_inicial
            fim_linha_final = conteudo_original.find('\n', pos_final_ancora + len(ancora_final))
            if fim_linha_final == -1:
                fim_linha_final = len(conteudo_original)
            
            fim_trecho = fim_linha_final
            trecho_encontrado = conteudo_original[inicio_trecho:fim_trecho]
            
            similaridade_base = calcular_similaridade_melhorada(texto_copiado, trecho_encontrado)
            
            # 🆕 CÁLCULO FINAL MATEMÁTICO: Similaridade base + bonus matemático
            similaridade_final = min(100.0, similaridade_base + score_matematico)
            
            print(f"🧮 Testando {arquivo}:")
            print(f"   📊 Similaridade base: {similaridade_base:.1f}%")
            print(f"   🎯 Score matemático: +{score_matematico:.1f}%")
            print(f"   🏆 Similaridade final: {similaridade_final:.1f}%")
            
            # 6. ✅ VALIDAÇÃO FINAL POR SIMILARIDADE MATEMÁTICA (CORRIGIDA v2.1.6)
            if similaridade_final >= limite_similaridade:
                posicoes_validadas = calcular_posicoes_precisas(conteudo_original, texto_copiado, arquivo, caminho_arquivo)
                
                if posicoes_validadas:
                    inicio_final = posicoes_validadas['inicio']
                    fim_final = posicoes_validadas['fim']
                    print(f"✅ Posições validadas por busca direta para {arquivo}")
                    
                    # 🆕 BONUS EXTRA: Se conseguiu validar posições precisas, é muito confiável
                    if bonus_precisao == 0:  # Só adiciona se não foi adicionado antes
                        similaridade_final = min(100.0, similaridade_final + 15.0)
                        print(f"🎯 {arquivo}: Bonus extra por validação precisa (+15.0% final)")
                else:
                    # 🚨 NOVO: Tenta busca com normalização de quebras
                    print(f"⚠️ Busca direta falhou, tentando com normalização de quebras...")
                    
                    # Normaliza quebras de linha
                    texto_normalizado = texto_copiado.replace('\r\n', '\n').replace('\r', '\n')
                    conteudo_normalizado = conteudo_original.replace('\r\n', '\n').replace('\r', '\n')
                    
                    # Busca no conteúdo normalizado
                    pos_normalizada = conteudo_normalizado.find(texto_normalizado)
                    
                    if pos_normalizada != -1:
                        print(f"✅ Encontrado após normalização na posição {pos_normalizada}")
                        
                        # Mapeia posição normalizada de volta para original
                        contador_norm = 0
                        pos_real = 0
                        
                        # Percorre o conteúdo original contando caracteres
                        for i, char in enumerate(conteudo_original):
                            if contador_norm >= pos_normalizada:
                                pos_real = i
                                break
                            
                            # Se for \r\n, conta como 1 no normalizado
                            if char == '\r' and i + 1 < len(conteudo_original) and conteudo_original[i + 1] == '\n':
                                continue  # Pula o \r
                            
                            contador_norm += 1
                        
                        # Calcula fim baseado no tamanho original
                        fim_real = pos_real
                        chars_originais = 0
                        
                        # Conta caracteres do texto original no conteúdo
                        for i in range(pos_real, len(conteudo_original)):
                            if chars_originais >= len(texto_copiado):
                                break
                            fim_real = i + 1
                            chars_originais += 1
                        
                        # Detecta BOM se houver
                        info_encoding = detectar_bom_e_encoding(caminho_arquivo)
                        offset_bom = info_encoding['bom_size'] if info_encoding['has_bom'] else 0
                        
                        inicio_final = pos_real + offset_bom
                        fim_final = fim_real + offset_bom
                        
                        print(f"📍 Posições calculadas: {inicio_final} até {fim_final}")
                        print(f"   🔧 Offset BOM: +{offset_bom} bytes")
                        
                        # Validação
                        texto_validacao = conteudo_original[pos_real:fim_real]
                        texto_validacao_norm = texto_validacao.replace('\r\n', '\n').replace('\r', '\n')
                        
                        if texto_validacao_norm == texto_normalizado:
                            print(f"✅ Validação OK: textos idênticos após normalização")
                        else:
                            print(f"⚠️ Validação parcial: pequenas diferenças detectadas")
                            
                    else:
                        # Último recurso: usa posições das âncoras
                        print(f"⚠️ Usando posições por âncoras (menos preciso)")
                        
                        # Detecta BOM para ajuste
                        info_encoding = detectar_bom_e_encoding(caminho_arquivo)
                        offset_bom = info_encoding['bom_size'] if info_encoding['has_bom'] else 0
                        
                        inicio_final = inicio_trecho + offset_bom
                        fim_final = fim_trecho + offset_bom
                        print(f"   🔧 Ajuste BOM aplicado: +{offset_bom} bytes")
                
                # Contexto com ajuste para possível BOM
                info_encoding = detectar_bom_e_encoding(caminho_arquivo)
                offset_contexto = info_encoding['bom_size'] if info_encoding['has_bom'] else 0
                
                contexto_inicio = max(0, inicio_final - 50)
                contexto_fim = min(len(conteudo_original) + offset_contexto, fim_final + 50)
                
                # Ajusta extração do contexto
                if offset_contexto > 0:
                    contexto_real_inicio = max(0, contexto_inicio - offset_contexto)
                    contexto_real_fim = min(len(conteudo_original), contexto_fim - offset_contexto)
                else:
                    contexto_real_inicio = contexto_inicio
                    contexto_real_fim = contexto_fim
                
                contexto_texto = conteudo_original[contexto_real_inicio:contexto_real_fim]
                
                arquivo_info = {
                    'nome': arquivo,
                    'caminho': caminho_arquivo,
                    'inicio': inicio_final,
                    'fim': fim_final,
                    'tamanho': len(texto_copiado),
                    'texto_original': texto_copiado,
                    'texto_encontrado': trecho_encontrado,
                    'similaridade': similaridade_final,
                    'contexto_inicio': contexto_inicio,
                    'contexto_fim': contexto_fim,
                    'contexto_texto': contexto_texto
                }
                
                adicionar_resultado_global(5, arquivo_info)
                arquivos_encontrados += 1
                print(f"✅ MATCH MATEMÁTICO ENCONTRADO - {arquivo} ({similaridade_final:.1f}%)")
                print(f"   🧮 Breakdown: {similaridade_base:.1f}% base + {score_matematico:.1f}% matemático + validações")
    
    if arquivos_encontrados > 0:
        print(f"\n🎯 RESUMO TIPO5: Texto encontrado em {arquivos_encontrados} arquivo(s) por estratégia matemática híbrida")
        print(f"🧮 Estratégia: Âncoras + TIPO3 no meio + cálculo matemático de probabilidade")
    else:
        print("❌ FAIL: Nenhum arquivo atendeu o critério de estratégia matemática híbrida")

# 🆕 TIPO 6: IGNORANDO TODOS OS U+000D (v2.1.2)
def tipo6_ignorar_carriage_returns(texto_copiado):
    """🆕 TIPO 6: Ignora completamente todos os U+000D (\\r) - HOTFIX v2.1.2"""
    print("🔍 TIPO 6: IGNORANDO COMPLETAMENTE TODOS OS U+000D (\\r)")
    print("Regra: Remove todos os \\r de ambos os textos, depois busca")
    
    texto_sem_cr = limpar_carriage_returns(texto_copiado)
    arquivos_encontrados = 0
    
    print(f"🧹 TEXTO ORIGINAL: {len(texto_copiado)} chars")
    print(f"🧹 TEXTO LIMPO: {len(texto_sem_cr)} chars")
    print(f"🧹 CRs REMOVIDOS: {len(texto_copiado) - len(texto_sem_cr)}")
    
    for raiz, _, arquivos in os.walk(PASTA_BASE):
        for arquivo in arquivos:
            ext = os.path.splitext(arquivo)[1].lower()
            if ext in EXTENSOES_NEGADAS or eh_arquivo_backup(arquivo):
                continue
                
            caminho_arquivo = os.path.join(raiz, arquivo)
            conteudo_original = ler_arquivo(caminho_arquivo)
            conteudo_sem_cr = limpar_carriage_returns(conteudo_original)
            
            if texto_sem_cr in conteudo_sem_cr:
                print(f"🔍 Calculando posições precisas para {arquivo} (TIPO6 - sem \\r)...")
                
                # 🚨 PASSA CAMINHO PARA CORREÇÃO BOM
                posicoes = calcular_posicoes_precisas(conteudo_original, texto_copiado, arquivo, caminho_arquivo)
                if not posicoes:
                    print(f"❌ Erro ao calcular posições para {arquivo}")
                    continue
                
                # 🔧 USA FUNÇÃO CORRIGIDA COM BOM
                if not validar_posicoes_com_bom(conteudo_original, posicoes, texto_copiado, caminho_arquivo, arquivo):
                    print(f"❌ Validação falhou para {arquivo}")
                    continue
                
                contexto_inicio = max(0, posicoes['inicio'] - 50)
                contexto_fim = min(len(conteudo_original) + 3, posicoes['fim'] + 50)  # +3 para BOM
                contexto_texto = conteudo_original[max(0, contexto_inicio-3):contexto_fim-3]  # Ajuste contexto
                
                arquivo_info = {
                    'nome': arquivo,
                    'caminho': caminho_arquivo,
                    'inicio': posicoes['inicio'],
                    'fim': posicoes['fim'],
                    'tamanho': len(texto_copiado),
                    'texto_original': texto_copiado,
                    'contexto_inicio': contexto_inicio,
                    'contexto_fim': contexto_fim,
                    'contexto_texto': contexto_texto
                }
                
                adicionar_resultado_global(6, arquivo_info)
                arquivos_encontrados += 1
                print(f"✅ ENCONTRADO - {arquivo} (ignorando \\r)")
    
    if arquivos_encontrados > 0:
        print(f"\n🎯 RESUMO TIPO6: Texto encontrado em {arquivos_encontrados} arquivo(s) ignorando todos os \\r")
    else:
        print("❌ FAIL")

# ═══════════════════════════════════════════════════════════════════════════════
# 🆕 SISTEMA CONSOLIDADO DE SALVAMENTO XML
# ═══════════════════════════════════════════════════════════════════════════════

def salvar_xml_consolidado(resultados: List[ResultadoBusca]):
    """Função unificada para salvar XML com resultados ordenados por confiabilidade"""
    if not resultados:
        print("⚠️ Nenhum resultado para salvar no XML")
        return
    
    resultados_ordenados = sorted(
        resultados,
        key=lambda r: (r.score_confiabilidade, r.similaridade or 0, r.nome_arquivo),
        reverse=True
    )
    
    print(f"\n🔄 ORDENANDO RESULTADOS POR CONFIABILIDADE:")
    for i, resultado in enumerate(resultados_ordenados, 1):
        score = resultado.score_confiabilidade
        sim_texto = f" (sim: {resultado.similaridade:.1f}%)" if resultado.similaridade else ""
        print(f"   {i}. 📁 {resultado.nome_arquivo} - TIPO{resultado.tipo} (score: {score:.1f}){sim_texto}")
    
    root = ET.Element("sessionlinner")
    
    info = ET.SubElement(root, "info")
    ET.SubElement(info, "timestamp").text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ET.SubElement(info, "versao").text = "2.1.6-CORRECAO-COMPLETA"
    ET.SubElement(info, "total_arquivos").text = str(len(resultados_ordenados))
    ET.SubElement(info, "tipos_busca_executados").text = ",".join(sorted(set(str(r.tipo) for r in resultados_ordenados)))
    ET.SubElement(info, "ordenacao").text = "score_confiabilidade DESC, similaridade DESC, nome ASC"
    
    # 🆕 SALVA CONFIGURAÇÕES DE QUALIDADE USADAS NA BUSCA (v2.1.1)
    configuracoes = ET.SubElement(info, "configuracoes_busca")
    ET.SubElement(configuracoes, "limite_probabilidade_melhor_resultado").text = str(LIMITE_PROBABILIDADE_MELHOR_RESULTADO)
    ET.SubElement(configuracoes, "limite_similaridade_tipo5").text = str(LIMITE_SIMILARIDADE_TIPO5)
    # 🆕 ADICIONA INFO SOBRE HOTFIX U+000D (v2.1.2)
    ET.SubElement(configuracoes, "hotfix_carriage_return").text = "true"
    ET.SubElement(configuracoes, "tipo6_ignorar_cr").text = "true"
    # 🚨 NOVA INFO SOBRE CORREÇÃO BOM
    ET.SubElement(configuracoes, "correcao_bom_utf8").text = "true"
    ET.SubElement(configuracoes, "encoding_automatico").text = "utf-8-sig"
    # 🆕 NOVA CORREÇÃO v2.1.6
    ET.SubElement(configuracoes, "correcao_quebras_linha").text = "true"
    ET.SubElement(configuracoes, "mapeamento_posicoes_preciso").text = "true"
    
    for i, resultado in enumerate(resultados_ordenados, 1):
        arquivo_elem = ET.SubElement(root, f"arquivo{i}")
        
        ET.SubElement(arquivo_elem, "nome").text = resultado.nome_arquivo
        ET.SubElement(arquivo_elem, "caminho_completo").text = resultado.caminho_completo
        
        confiabilidade = ET.SubElement(arquivo_elem, "confiabilidade")
        ET.SubElement(confiabilidade, "tipo_busca").text = str(resultado.tipo)
        ET.SubElement(confiabilidade, "score_confiabilidade").text = f"{resultado.score_confiabilidade:.2f}"
        if resultado.similaridade is not None:
            ET.SubElement(confiabilidade, "similaridade_percentual").text = f"{resultado.similaridade:.2f}"
        
        posicoes = ET.SubElement(arquivo_elem, "posicoes")
        ET.SubElement(posicoes, "inicio").text = str(resultado.posicao_inicio)
        ET.SubElement(posicoes, "fim").text = str(resultado.posicao_fim)
        ET.SubElement(posicoes, "tamanho_texto").text = str(resultado.tamanho_texto)
        
        validacao = ET.SubElement(posicoes, "validacao")
        ET.SubElement(validacao, "posicoes_validadas").text = "true"
        ET.SubElement(validacao, "metodo_calculo").text = "calcular_posicoes_precisas_v2_1_6_CORRECAO_COMPLETA"
        ET.SubElement(validacao, "hotfix_carriage_return").text = "aplicado"
        ET.SubElement(validacao, "correcao_bom_utf8").text = "aplicado"
        ET.SubElement(validacao, "mapeamento_quebras_linha").text = "aplicado"
        
        texto_elem = ET.SubElement(arquivo_elem, "texto_encontrado")
        ET.SubElement(texto_elem, "original").text = resultado.texto_original
        ET.SubElement(texto_elem, "repr_original").text = repr(resultado.texto_original)
        if resultado.texto_encontrado:
            ET.SubElement(texto_elem, "encontrado").text = resultado.texto_encontrado
            ET.SubElement(texto_elem, "repr_encontrado").text = repr(resultado.texto_encontrado)
        
        contexto = ET.SubElement(arquivo_elem, "contexto")
        ET.SubElement(contexto, "inicio_contexto").text = str(resultado.contexto_inicio)
        ET.SubElement(contexto, "fim_contexto").text = str(resultado.contexto_fim)
        ET.SubElement(contexto, "texto_contexto").text = resultado.contexto_texto
    
    try:
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write("sessionlinner.xml", encoding="utf-8", xml_declaration=True)
        
        print(f"\n💾 XML CONSOLIDADO SALVO COM SUCESSO!")
        print(f"   📁 Arquivo: sessionlinner.xml")
        print(f"   📊 Total de resultados: {len(resultados_ordenados)}")
        print(f"   🆕 Versão: 2.1.6-CORRECAO-COMPLETA (quebras de linha + BOM)")
        
        # 🆕 CONTROLE DE QUALIDADE: Só mostra como "melhor resultado" se atender critério de probabilidade (v2.1.1)
        melhor_resultado = resultados_ordenados[0]
        probabilidade_melhor = melhor_resultado.similaridade if melhor_resultado.similaridade is not None else 100.0
        
        if probabilidade_melhor >= LIMITE_PROBABILIDADE_MELHOR_RESULTADO:
            print(f"   🏆 Melhor resultado: {melhor_resultado.nome_arquivo} (TIPO{melhor_resultado.tipo}, score: {melhor_resultado.score_confiabilidade:.1f}, prob: {probabilidade_melhor:.1f}%)")
        else:
            print(f"   📊 Primeiro resultado: {melhor_resultado.nome_arquivo} (TIPO{melhor_resultado.tipo}, score: {melhor_resultado.score_confiabilidade:.1f}, prob: {probabilidade_melhor:.1f}%)")
            print(f"   ⚠️ Aviso: Probabilidade {probabilidade_melhor:.1f}% < {LIMITE_PROBABILIDADE_MELHOR_RESULTADO:.1f}% (limite mínimo para 'melhor resultado')")
        
    except Exception as e:
        print(f"❌ ERRO ao salvar XML consolidado: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 FUNÇÃO DE LEITURA XML
# ═══════════════════════════════════════════════════════════════════════════════

def ler_xml_posicoes(arquivo_especifico=None):
    """Lê XML e sempre retorna o de MAIOR SCORE"""
    if not os.path.exists("sessionlinner.xml"):
        print("❌ ERRO: Arquivo sessionlinner.xml não encontrado!")
        print("   Execute primeiro: python pythonsearch.py (sem parâmetros)")
        return None
    
    try:
        tree = ET.parse("sessionlinner.xml")
        root = tree.getroot()
        
        versao_elem = root.find('info/versao')
        versao = versao_elem.text if versao_elem is not None else "anterior"
        print(f"📋 Carregando XML versão: {versao}")
        
        # 🆕 VERIFICA SE TEM HOTFIX U+000D (v2.1.2)
        hotfix_elem = root.find('info/configuracoes_busca/hotfix_carriage_return')
        if hotfix_elem is not None and hotfix_elem.text == "true":
            print("🔧 XML com HOTFIX U+000D ativado")
        else:
            print("⚠️ XML sem HOTFIX U+000D (versão anterior)")
        
        # 🚨 VERIFICA CORREÇÃO BOM
        bom_elem = root.find('info/configuracoes_busca/correcao_bom_utf8')
        if bom_elem is not None and bom_elem.text == "true":
            print("🔧 XML com CORREÇÃO BOM UTF-8 ativada")
        else:
            print("⚠️ XML sem correção BOM (versão anterior)")
        
        # 🆕 VERIFICA CORREÇÃO QUEBRAS v2.1.6
        quebras_elem = root.find('info/configuracoes_busca/correcao_quebras_linha')
        if quebras_elem is not None and quebras_elem.text == "true":
            print("🔧 XML com CORREÇÃO QUEBRAS DE LINHA ativada")
        else:
            print("⚠️ XML sem correção quebras de linha (versão anterior)")
        
        # 🆕 INFO SOBRE FILTRO DE BACKUP (v2.1.4)
        if versao in ['2.1.4', '2.1.4-CORRECAO-BOM', '2.1.6-CORRECAO-COMPLETA']:
            print("🗂️ Filtro de arquivos de backup ativado")
        
        # 🆕 LÊ CONFIGURAÇÕES DE QUALIDADE SALVAS NO XML (v2.1.1)
        limite_probabilidade_xml = None
        limite_prob_elem = root.find('info/configuracoes_busca/limite_probabilidade_melhor_resultado')
        if limite_prob_elem is not None:
            limite_probabilidade_xml = float(limite_prob_elem.text)
            print(f"🎯 Limite de probabilidade usado na busca: {limite_probabilidade_xml:.1f}%")
            if limite_probabilidade_xml != LIMITE_PROBABILIDADE_MELHOR_RESULTADO:
                print(f"⚠️ Aviso: Limite atual ({LIMITE_PROBABILIDADE_MELHOR_RESULTADO:.1f}%) difere do usado na busca ({limite_probabilidade_xml:.1f}%)")
        else:
            limite_probabilidade_xml = LIMITE_PROBABILIDADE_MELHOR_RESULTADO  # Fallback para XMLs antigos
        
        if arquivo_especifico:
            print(f"🔍 BUSCANDO ARQUIVO ESPECÍFICO: {arquivo_especifico}")
            
            melhor_resultado = None
            melhor_score = -1
            
            for i in range(1, 21):
                arquivo_elem = root.find(f'arquivo{i}')
                if arquivo_elem is None:
                    continue
                
                nome_arquivo = arquivo_elem.find('nome').text
                if nome_arquivo == arquivo_especifico:
                    score_elem = arquivo_elem.find('confiabilidade/score_confiabilidade')
                    score = float(score_elem.text) if score_elem is not None else 0
                    
                    if score > melhor_score:
                        melhor_score = score
                        
                        similaridade_elem = arquivo_elem.find('confiabilidade/similaridade_percentual') or arquivo_elem.find('similaridade_percentual')
                        similaridade = float(similaridade_elem.text) if similaridade_elem is not None else None
                        
                        melhor_resultado = {
                            'arquivo': nome_arquivo,
                            'caminho': arquivo_elem.find('caminho_completo').text,
                            'inicio': int(arquivo_elem.find('posicoes/inicio').text),
                            'fim': int(arquivo_elem.find('posicoes/fim').text),
                            'timestamp': root.find('info/timestamp').text,
                            'similaridade': similaridade,
                            'score': score,
                            'tipo': arquivo_elem.find('confiabilidade/tipo_busca').text if arquivo_elem.find('confiabilidade/tipo_busca') is not None else "?",
                            'limite_probabilidade_busca': limite_probabilidade_xml,  # 🆕 Passa o limite usado na busca
                            'versao': versao
                        }
            
            if melhor_resultado:
                print("📋 MELHOR RESULTADO ENCONTRADO (ARQUIVO ESPECÍFICO):")
                print(f"   📁 Arquivo: {melhor_resultado['arquivo']}")
                print(f"   📍 Posição: {melhor_resultado['inicio']} até {melhor_resultado['fim']}")
                print(f"   🏆 Score: {melhor_resultado['score']:.1f} (TIPO{melhor_resultado['tipo']})")
                if melhor_resultado['similaridade']:
                    print(f"   🎯 Similaridade: {melhor_resultado['similaridade']:.1f}%")
                    # 🆕 CONTROLE DE QUALIDADE: Usa limite da busca original (v2.1.1)
                    limite_usado = melhor_resultado.get('limite_probabilidade_busca', limite_probabilidade_xml)
                    if melhor_resultado['similaridade'] < limite_usado:
                        print(f"   ⚠️ Aviso: Probabilidade {melhor_resultado['similaridade']:.1f}% < {limite_usado:.1f}% (abaixo do limite usado na busca)")
                print(f"   🕒 Salvo em: {melhor_resultado['timestamp']}")
                return melhor_resultado
            
            print(f"❌ ERRO: Arquivo '{arquivo_especifico}' não encontrado no XML!")
            print("📋 ARQUIVOS DISPONÍVEIS:")
            for i in range(1, 21):
                arquivo_elem = root.find(f'arquivo{i}')
                if arquivo_elem is not None:
                    nome = arquivo_elem.find('nome').text
                    score_elem = arquivo_elem.find('confiabilidade/score_confiabilidade')
                    score_texto = f" (score: {float(score_elem.text):.1f})" if score_elem is not None else ""
                    print(f"   {i}. 📁 {nome}{score_texto}")
            return None
        
        arquivo_elem = root.find('arquivo1')
        if arquivo_elem is None:
            print("❌ ERRO: Nenhum arquivo encontrado no XML!")
            return None
        
        score_elem = arquivo_elem.find('confiabilidade/score_confiabilidade')
        score = float(score_elem.text) if score_elem is not None else 0
        
        tipo_elem = arquivo_elem.find('confiabilidade/tipo_busca')
        tipo = tipo_elem.text if tipo_elem is not None else "?"
        
        similaridade_elem = arquivo_elem.find('confiabilidade/similaridade_percentual') or arquivo_elem.find('similaridade_percentual')
        similaridade = float(similaridade_elem.text) if similaridade_elem is not None else None
        
        info = {
            'arquivo': arquivo_elem.find('nome').text,
            'caminho': arquivo_elem.find('caminho_completo').text,
            'inicio': int(arquivo_elem.find('posicoes/inicio').text),
            'fim': int(arquivo_elem.find('posicoes/fim').text),
            'timestamp': root.find('info/timestamp').text,
            'similaridade': similaridade,
            'score': score,
            'tipo': tipo,
            'limite_probabilidade_busca': limite_probabilidade_xml,  # 🆕 Passa o limite usado na busca
            'versao': versao
        }
        
        print("📋 RESULTADO DE MAIOR CONFIABILIDADE CARREGADO:")
        print(f"   📁 Arquivo: {info['arquivo']}")
        print(f"   📍 Posição: {info['inicio']} até {info['fim']}")
        print(f"   🏆 Score: {info['score']:.1f} (TIPO{info['tipo']})")
        if similaridade:
            print(f"   🎯 Similaridade: {similaridade:.1f}%")
            # 🆕 CONTROLE DE QUALIDADE: Usa limite da busca original (v2.1.1)
            if similaridade < limite_probabilidade_xml:
                print(f"   ⚠️ Aviso: Probabilidade {similaridade:.1f}% < {limite_probabilidade_xml:.1f}% (abaixo do limite usado na busca)")
        print(f"   🕒 Salvo em: {info['timestamp']}")
        
        return info
        
    except Exception as e:
        print(f"❌ ERRO ao ler XML: {e}")
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 FUNÇÃO PASTE CORRIGIDA v2.1.6
# ═══════════════════════════════════════════════════════════════════════════════

def colar_nas_coordenadas(arquivo_especifico=None):
    """Cola o conteúdo do Ctrl+C nas coordenadas salvas com CORREÇÃO AUTOMÁTICA v2.1.6"""
    if arquivo_especifico:
        print(f"📋 MODO PASTE ESPECÍFICO: {arquivo_especifico}")
    else:
        print("📋 MODO PASTE: Colando nas coordenadas salvas")
    print("=" * 80)
    
    posicoes = ler_xml_posicoes(arquivo_especifico)
    if not posicoes:
        return
    
    texto_novo = obter_texto_copiado()
    if not texto_novo:
        print("❌ ERRO: Nenhum texto na área de transferência para colar!")
        return
    
    print(f"\n📝 TEXTO A SER COLADO:")
    mostrar_debug_texto(texto_novo, "NOVO CONTEÚDO")
    
    # 🆕 DETECTA PROBLEMAS COM U+000D NO TEXTO NOVO (v2.1.2)
    tem_problemas_cr = detectar_problemas_carriage_return(texto_novo)
    if tem_problemas_cr:
        print("⚠️ AVISO: Texto contém carriage returns isolados (\\r)")
        print("   Recomenda-se executar nova busca com TIPO6 se houver problemas")
    
    if not os.path.exists(posicoes['caminho']):
        print(f"❌ ERRO: Arquivo não encontrado: {posicoes['caminho']}")
        return
    
    try:
        # 🚨 CORREÇÃO: Usa leitura corrigida com BOM
        conteudo_original = ler_arquivo(posicoes['caminho'])
        
        print(f"\n📁 ARQUIVO CARREGADO: {posicoes['arquivo']}")
        print(f"   📏 Tamanho original: {len(conteudo_original)} caracteres")
        print(f"   🔧 XML versão: {posicoes.get('versao', 'anterior')}")
        
        # 🚨 CORREÇÃO AUTOMÁTICA DE COORDENADAS v2.1.6
        info_encoding = detectar_bom_e_encoding(posicoes['caminho'])
        offset_bom = info_encoding['bom_size'] if info_encoding['has_bom'] else 0
        
        # Ajusta coordenadas removendo offset BOM (pois conteúdo foi lido sem BOM)
        inicio_ajustado = posicoes['inicio'] - offset_bom
        fim_ajustado = posicoes['fim'] - offset_bom
        
        print(f"\n🔧 AJUSTE DE COORDENADAS:")
        print(f"   📍 Coordenadas XML: {posicoes['inicio']} até {posicoes['fim']}")
        print(f"   🔖 Offset BOM: {offset_bom} bytes")
        print(f"   📍 Coordenadas ajustadas: {inicio_ajustado} até {fim_ajustado}")
        
        # Verifica se o texto nas posições bate com o esperado
        deve_buscar = False
        
        if inicio_ajustado < 0 or fim_ajustado > len(conteudo_original) or inicio_ajustado >= fim_ajustado:
            print(f"⚠️ Coordenadas fora dos limites válidos")
            deve_buscar = True
        else:
            texto_atual_posicoes = conteudo_original[inicio_ajustado:fim_ajustado]
            
            if not texto_atual_posicoes or len(texto_atual_posicoes) != len(texto_novo):
                print(f"⚠️ Tamanhos diferentes: atual={len(texto_atual_posicoes)}, novo={len(texto_novo)}")
                deve_buscar = True
            else:
                # Compara normalizando quebras
                texto_atual_norm = texto_atual_posicoes.replace('\r\n', '\n').replace('\r', '\n')
                texto_novo_norm = texto_novo.replace('\r\n', '\n').replace('\r', '\n')
                
                if texto_atual_norm != texto_novo_norm:
                    print(f"⚠️ Conteúdos diferentes após normalização")
                    deve_buscar = True
        
        if deve_buscar:
            print(f"\n🔍 BUSCANDO POSIÇÃO CORRETA (coordenadas podem estar desatualizadas)...")
            
            # Tenta busca direta primeiro
            pos_direta = conteudo_original.find(texto_novo)
            
            if pos_direta == -1:
                # Tenta com normalização
                texto_novo_norm = texto_novo.replace('\r\n', '\n').replace('\r', '\n')
                conteudo_norm = conteudo_original.replace('\r\n', '\n').replace('\r', '\n')
                pos_norm = conteudo_norm.find(texto_novo_norm)
                
                if pos_norm != -1:
                    print(f"✅ Encontrado após normalização na posição {pos_norm}")
                    
                    # Mapeia de volta para original
                    contador = 0
                    for i, char in enumerate(conteudo_original):
                        if contador >= pos_norm:
                            pos_direta = i
                            break
                        if char == '\r' and i + 1 < len(conteudo_original) and conteudo_original[i + 1] == '\n':
                            continue
                        contador += 1
            
            if pos_direta != -1:
                inicio_ajustado = pos_direta
                fim_ajustado = pos_direta + len(texto_novo)
                print(f"✅ POSIÇÃO CORRETA ENCONTRADA: {inicio_ajustado} até {fim_ajustado}")
                print(f"   📊 Diferença das coordenadas XML: {inicio_ajustado - (posicoes['inicio'] - offset_bom)} chars")
            else:
                print(f"❌ AVISO: Não foi possível encontrar o texto exato no arquivo!")
                print(f"   Continuando com coordenadas do XML (podem estar incorretas)")
        
        # Usa as coordenadas ajustadas
        inicio = inicio_ajustado
        fim = fim_ajustado
        
        if inicio < 0 or fim > len(conteudo_original) or inicio >= fim:
            print(f"❌ ERRO: Coordenadas inválidas!")
            print(f"   📍 Início: {inicio}, Fim: {fim}")
            print(f"   📏 Tamanho do arquivo: {len(conteudo_original)}")
            return
        
        texto_atual_nas_posicoes = conteudo_original[inicio:fim]
        print(f"\n🔍 VALIDAÇÃO DAS POSIÇÕES:")
        print(f"   📍 Posições: {inicio} → {fim}")
        print(f"   📏 Tamanho esperado: {fim - inicio} caracteres")
        print(f"   📏 Texto atual nessas posições: {len(texto_atual_nas_posicoes)} caracteres")
        print(f"   📋 Conteúdo atual: {repr(texto_atual_nas_posicoes[:100])}")
        
        # 🆕 VALIDAÇÃO EXTRA COM HOTFIX U+000D (v2.1.2)
        if posicoes.get('versao') in ['2.1.2', '2.1.3', '2.1.4', '2.1.4-CORRECAO-BOM', '2.1.6-CORRECAO-COMPLETA']:
            print("🔧 VALIDAÇÃO COM CORREÇÕES APLICADAS:")
            texto_atual_sem_cr = limpar_carriage_returns(texto_atual_nas_posicoes)
            texto_novo_sem_cr = limpar_carriage_returns(texto_novo)
            if texto_atual_sem_cr == texto_novo_sem_cr:
                print("   ✅ Textos idênticos após remover \\r (CORREÇÕES validadas)")
            else:
                # Tenta validação com normalização
                texto_atual_norm = texto_atual_nas_posicoes.replace('\r\n', '\n').replace('\r', '\n')
                texto_novo_norm = texto_novo.replace('\r\n', '\n').replace('\r', '\n')
                if texto_atual_norm == texto_novo_norm:
                    print("   ✅ Textos idênticos após normalizar quebras (CORREÇÕES validadas)")
                else:
                    print("   ⚠️ Textos diferentes mesmo após correções")
        
        texto_antigo = conteudo_original[inicio:fim]
        print(f"\n🔄 SUBSTITUIÇÃO:")
        print(f"   📍 Posições: {inicio} → {fim}")
        print(f"   📏 Tamanho antigo: {len(texto_antigo)} caracteres")
        print(f"   📏 Tamanho novo: {len(texto_novo)} caracteres")
        print(f"   ❌ Texto antigo: {repr(texto_antigo[:100])}")
        print(f"   ✅ Texto novo: {repr(texto_novo[:100])}")
        
        texto_novo_final = texto_novo
        novo_conteudo = conteudo_original[:inicio] + texto_novo_final + conteudo_original[fim:]
        
        # 🚨 CORREÇÃO: Salva com encoding UTF-8 sem BOM (padrão)
        with open(posicoes['caminho'], 'w', encoding='utf-8', newline='') as f:
            f.write(novo_conteudo)
        
        print(f"\n✅ PASTE REALIZADO COM SUCESSO!")
        print(f"   📁 Arquivo: {posicoes['arquivo']}")
        print(f"   📏 Novo tamanho: {len(novo_conteudo)} caracteres")
        print(f"   📝 Diferença: {len(novo_conteudo) - len(conteudo_original):+d} caracteres")
        
        # Verificação usando leitura corrigida
        conteudo_verificacao = ler_arquivo(posicoes['caminho'])
        
        if len(conteudo_verificacao) == len(novo_conteudo):
            print("✅ Verificação: Arquivo salvo corretamente!")
            
            texto_verificacao = conteudo_verificacao[inicio:inicio + len(texto_novo)]
            if texto_verificacao == texto_novo:
                print("✅ Verificação final: Texto colado exatamente na posição correta!")
            else:
                print("⚠️ Aviso: Texto pode ter sido colado com pequenos ajustes de formatação")
        else:
            print("⚠️ Aviso: Tamanho do arquivo diferente do esperado após salvamento")
        
    except Exception as e:
        print(f"❌ ERRO ao processar arquivo: {e}")
        import traceback
        traceback.print_exc()

def criar_backup_antes_paste(caminho_arquivo):
    """Cria backup do arquivo antes de fazer modificações no modo paste com verificação de timezone"""
    try:
        if not os.path.exists(caminho_arquivo):
            print(f"❌ ERRO: Arquivo não encontrado para backup: {caminho_arquivo}")
            return False
        
        diretorio_arquivo = os.path.dirname(caminho_arquivo)
        nome_arquivo = os.path.basename(caminho_arquivo)
        
        pasta_backup = os.path.join(diretorio_arquivo, "Backup")
        if not os.path.exists(pasta_backup):
            os.makedirs(pasta_backup)
            print(f"📁 Pasta Backup criada: {pasta_backup}")
        
        # 🆕 OBTER INFORMAÇÕES DE TEMPO DO ARQUIVO ORIGINAL
        stat_original = os.stat(caminho_arquivo)
        mtime_original = datetime.fromtimestamp(stat_original.st_mtime)
        
        temp_backup = os.path.join(pasta_backup, f"{nome_arquivo}.temp.bak")
        shutil.copy2(caminho_arquivo, temp_backup)
        
        # 🆕 TIMESTAMP SINCRONIZADO COM VERIFICAÇÃO DE TIMEZONE
        import time
        agora = datetime.now()
        agora_real = datetime.fromtimestamp(time.time())  # Força timestamp real do sistema
        timestamp = agora_real.strftime("%Y-%m-%d_%H-%M-%S")
        
        # 🆕 DIAGNÓSTICO DE SINCRONIZAÇÃO
        diferenca_datetime = abs((agora - agora_real).total_seconds())
        if diferenca_datetime > 5:
            print(f"⚠️ DETECTADA DIFERENÇA DE {diferenca_datetime:.0f}s entre datetime.now() e time.time()")
            print(f"   🕒 datetime.now(): {agora.strftime('%H:%M:%S')}")
            print(f"   🕒 time.time(): {agora_real.strftime('%H:%M:%S')}")
        
        nome_backup = f"{nome_arquivo}.backup_{timestamp}.bak"
        caminho_backup = os.path.join(pasta_backup, nome_backup)
        
        os.rename(temp_backup, caminho_backup)
        
        # 🆕 PRESERVAR TIMESTAMPS DO ARQUIVO ORIGINAL NO BACKUP
        os.utime(caminho_backup, (stat_original.st_atime, stat_original.st_mtime))
        
        # 🆕 VERIFICAÇÃO DE TIMEZONE E RELATÓRIO DETALHADO
        stat_backup = os.stat(caminho_backup)
        mtime_backup = datetime.fromtimestamp(stat_backup.st_mtime)
        diferenca_horas = abs((agora - mtime_original).total_seconds() / 3600)
        
        print(f"💾 BACKUP CRIADO:")
        print(f"   📁 Original: {nome_arquivo}")
        print(f"   💾 Backup: {nome_backup}")
        print(f"   📂 Local: {pasta_backup}")
        print(f"   🕒 VERIFICAÇÃO DE TIMESTAMP:")
        print(f"      📅 Arquivo original: {mtime_original.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      📅 Backup criado: {agora.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      📅 Backup preservado: {mtime_backup.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      ⏰ Diferença temporal: {diferenca_horas:.1f} horas")
        
        # 🆕 ALERTA PARA PROBLEMAS DE TIMEZONE
        if diferenca_horas > 3:
            print(f"   ⚠️ AVISO: Diferença de {diferenca_horas:.1f}h pode indicar problema de timezone")
            print(f"   🔧 Sistema detectou possível diferença de fuso horário")
        else:
            print(f"   ✅ Timestamps consistentes (diferença: {diferenca_horas:.1f}h)")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO ao criar backup: {e}")
        import traceback
        traceback.print_exc()
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# 🆕 MODO BUSCA ATUALIZADO (v2.1.6)
# ═══════════════════════════════════════════════════════════════════════════════

def modo_busca():
    """Modo busca com consolidação global de resultados e CORREÇÃO COMPLETA v2.1.6"""
    print("🚀 CTRLCSEARCH.PY v2.1.6 - CORREÇÃO COMPLETA QUEBRAS DE LINHA")
    print("=" * 80)
    
    texto_copiado = obter_texto_copiado()
    
    if not texto_copiado:
        print("❌ ERRO: Nenhum texto na área de transferência!")
        return
    
    limpar_resultados_globais()
    mostrar_debug_texto(texto_copiado, "TEXTO COPIADO")
    
    # 🆕 ANÁLISE INICIAL DE CARRIAGE RETURNS (v2.1.2)
    tem_problemas_cr = detectar_problemas_carriage_return(texto_copiado)
    if tem_problemas_cr:
        print("🔧 HOTFIX U+000D: Detectados carriage returns isolados!")
        print("   TIPO6 será executado para tratamento específico")
    
    print("\n" + "=" * 80)
    tipo1_comparacao_literal(texto_copiado)
    
    print("\n" + "=" * 80)
    tipo2_comparacao_arquivo_completo(texto_copiado)
    
    print("\n" + "=" * 80)
    tipo3_comparacao_quebras_normalizadas(texto_copiado)
    
    print("\n" + "=" * 80)
    tipo4_comparacao_strip_aplicado(texto_copiado)
    
    print("\n" + "=" * 80)
    tipo5_busca_por_probabilidade(texto_copiado, limite_similaridade=LIMITE_SIMILARIDADE_TIPO5)
    
    # 🆕 TIPO 6: HOTFIX PARA U+000D (v2.1.2)
    print("\n" + "=" * 80)
    tipo6_ignorar_carriage_returns(texto_copiado)
    
    print("\n" + "=" * 80)
    print("🏁 ANÁLISE COMPLETA FINALIZADA (v2.1.6 - CORREÇÃO COMPLETA)")
    
    if resultados_globais:
        print(f"\n📊 TOTAL DE RESULTADOS COLETADOS: {len(resultados_globais)}")
        print("🔄 Iniciando consolidação e ordenação...")
        salvar_xml_consolidado(resultados_globais)
    else:
        print("\nℹ️ Nenhuma posição foi encontrada (nenhum match em qualquer tipo)")

# ═══════════════════════════════════════════════════════════════════════════════
# 🆕 DIAGNÓSTICO MELHORADO v2.1.6
# ═══════════════════════════════════════════════════════════════════════════════

def diagnosticar_caso_especifico():
    """🆕 Diagnóstico melhorado que detecta todos os problemas possíveis v2.1.6"""
    print("\n" + "=" * 80)
    print("🚨 DIAGNÓSTICO COMPLETO - ANÁLISE DE PROBLEMAS DE COORDENADAS")
    print("=" * 80)
    
    arquivo_path = r"C:\Users\arquivo.js"
    texto_copiado = obter_texto_copiado()
    
    if not texto_copiado:
        print("❌ Nenhum texto na área de transferência!")
        return
    
    if not os.path.exists(arquivo_path):
        print(f"❌ Arquivo não encontrado: {arquivo_path}")
        return
    
    # 1. Análise do BOM
    info_encoding = detectar_bom_e_encoding(arquivo_path)
    print(f"📄 ANÁLISE DO ARQUIVO: uiRenderer.js")
    print(f"🔖 Encoding: {info_encoding['detected']}")
    print(f"🔖 Tem BOM: {info_encoding['has_bom']} ({info_encoding['bom_size']} bytes)")
    
    # 2. Análise de quebras de linha
    print(f"\n📊 ANÁLISE DE QUEBRAS DE LINHA:")
    
    # Texto copiado
    cr_copiado = texto_copiado.count('\r')
    lf_copiado = texto_copiado.count('\n')
    crlf_copiado = texto_copiado.count('\r\n')
    print(f"📋 Texto copiado:")
    print(f"   \\r (CR): {cr_copiado}")
    print(f"   \\n (LF): {lf_copiado}")
    print(f"   \\r\\n (CRLF): {crlf_copiado}")
    print(f"   Tipo: {'Windows (CRLF)' if crlf_copiado > 0 else 'Unix (LF)' if lf_copiado > 0 else 'Sem quebras'}")
    
    # Arquivo
    conteudo = ler_arquivo_corrigido_bom(arquivo_path)
    cr_arquivo = conteudo.count('\r')
    lf_arquivo = conteudo.count('\n')
    crlf_arquivo = conteudo.count('\r\n')
    print(f"📁 Arquivo:")
    print(f"   \\r (CR): {cr_arquivo}")
    print(f"   \\n (LF): {lf_arquivo}")
    print(f"   \\r\\n (CRLF): {crlf_arquivo}")
    print(f"   Tipo: {'Windows (CRLF)' if crlf_arquivo > 0 else 'Unix (LF)' if lf_arquivo > 0 else 'Sem quebras'}")
    
    if (crlf_copiado > 0 and crlf_arquivo == 0) or (crlf_copiado == 0 and crlf_arquivo > 0):
        print(f"🚨 PROBLEMA DETECTADO: Quebras de linha incompatíveis!")
    
    # 3. Testes de busca
    print(f"\n🔍 TESTES DE BUSCA:")
    
    # Busca direta
    pos_direta = conteudo.find(texto_copiado)
    print(f"1. Busca direta: {'✅ ENCONTRADO' if pos_direta != -1 else '❌ NÃO ENCONTRADO'}")
    if pos_direta != -1:
        print(f"   📍 Posição: {pos_direta}")
    
    # Busca normalizada
    texto_norm = texto_copiado.replace('\r\n', '\n').replace('\r', '\n')
    conteudo_norm = conteudo.replace('\r\n', '\n').replace('\r', '\n')
    pos_norm = conteudo_norm.find(texto_norm)
    print(f"2. Busca normalizada: {'✅ ENCONTRADO' if pos_norm != -1 else '❌ NÃO ENCONTRADO'}")
    if pos_norm != -1:
        print(f"   📍 Posição normalizada: {pos_norm}")
    
    # Busca primeira linha
    primeira_linha = texto_copiado.split('\n')[0].strip().replace('\r', '')
    pos_primeira = conteudo.find(primeira_linha)
    print(f"3. Busca primeira linha: {'✅ ENCONTRADO' if pos_primeira != -1 else '❌ NÃO ENCONTRADO'}")
    if pos_primeira != -1:
        print(f"   📍 Posição: {pos_primeira}")
        print(f"   📝 Linha: {repr(primeira_linha[:50])}")
    
    # 4. Cálculo de coordenadas corretas
    if pos_norm != -1:
        print(f"\n📐 CÁLCULO DE COORDENADAS CORRETAS:")
        
        # Mapeia posição normalizada para original
        contador = 0
        pos_real = 0
        for i, char in enumerate(conteudo):
            if contador >= pos_norm:
                pos_real = i
                break
            if char == '\r' and i + 1 < len(conteudo) and conteudo[i + 1] == '\n':
                continue
            contador += 1
        
        # Calcula fim
        fim_real = pos_real + len(texto_copiado)
        
        # Ajusta para BOM se necessário
        pos_final = pos_real + info_encoding['bom_size']
        fim_final = fim_real + info_encoding['bom_size']
        
        print(f"   📍 Posição real (sem BOM): {pos_real} até {fim_real}")
        print(f"   📍 Posição final (com BOM): {pos_final} até {fim_final}")
        print(f"   📏 Tamanho: {len(texto_copiado)} chars")
        
        # Validação
        texto_extraido = conteudo[pos_real:fim_real]
        texto_extraido_norm = texto_extraido.replace('\r\n', '\n').replace('\r', '\n')
        if texto_extraido_norm == texto_norm:
            print(f"   ✅ VALIDAÇÃO: Textos idênticos após normalização")
        else:
            print(f"   ⚠️ VALIDAÇÃO: Diferenças encontradas")
            print(f"      Extraído: {repr(texto_extraido[:50])}")
            print(f"      Esperado: {repr(texto_copiado[:50])}")
    
    # 5. Comparação com XML
    if os.path.exists("sessionlinner.xml"):
        print(f"\n📋 COMPARAÇÃO COM XML ATUAL:")
        try:
            tree = ET.parse("sessionlinner.xml")
            root = tree.getroot()
            arquivo1 = root.find('arquivo1')
            if arquivo1:
                inicio_xml = int(arquivo1.find('posicoes/inicio').text)
                fim_xml = int(arquivo1.find('posicoes/fim').text)
                print(f"   📍 Coordenadas no XML: {inicio_xml} até {fim_xml}")
                
                if pos_norm != -1:
                    diferenca_inicio = inicio_xml - (pos_real + info_encoding['bom_size'])
                    diferenca_fim = fim_xml - (fim_real + info_encoding['bom_size'])
                    print(f"   📊 Diferença início: {diferenca_inicio:+d} chars")
                    print(f"   📊 Diferença fim: {diferenca_fim:+d} chars")
                    
                    if diferenca_inicio != 0:
                        print(f"   🚨 COORDENADAS INCORRETAS NO XML!")
        except:
            pass
    
    # 6. Teste da função corrigida
    print(f"\n🔧 TESTE DA FUNÇÃO calcular_posicoes_precisas v2.1.6:")
    posicoes_corrigidas = calcular_posicoes_precisas(conteudo, texto_copiado, "uiRenderer.js", arquivo_path)
    
    if posicoes_corrigidas:
        print(f"   ✅ FUNÇÃO FUNCIONANDO:")
        print(f"      📍 Início: {posicoes_corrigidas['inicio']}")
        print(f"      📍 Fim: {posicoes_corrigidas['fim']}")
        
        # Validação da função
        inicio_sem_bom = posicoes_corrigidas['inicio'] - info_encoding['bom_size']
        fim_sem_bom = posicoes_corrigidas['fim'] - info_encoding['bom_size']
        
        if inicio_sem_bom >= 0 and fim_sem_bom <= len(conteudo):
            texto_funcao = conteudo[inicio_sem_bom:fim_sem_bom]
            texto_funcao_norm = texto_funcao.replace('\r\n', '\n').replace('\r', '\n')
            
            if texto_funcao_norm == texto_norm:
                print(f"   ✅ VALIDAÇÃO DA FUNÇÃO: Perfeita!")
            else:
                print(f"   ⚠️ VALIDAÇÃO DA FUNÇÃO: Pequenas diferenças")
        else:
            print(f"   ❌ VALIDAÇÃO DA FUNÇÃO: Coordenadas fora dos limites")
    else:
        print(f"   ❌ FUNÇÃO RETORNOU None")
    
    print(f"\n🎯 RESUMO E RECOMENDAÇÕES:")
    if crlf_copiado > 0 and crlf_arquivo == 0:
        print(f"   🚨 Problema principal: Texto tem CRLF mas arquivo tem apenas LF")
        print(f"   🔧 Solução: O script v2.1.6 já trata isso automaticamente")
    elif info_encoding['has_bom']:
        print(f"   🚨 Problema secundário: Arquivo tem BOM UTF-8")
        print(f"   🔧 Solução: Ajustar coordenadas em +{info_encoding['bom_size']} bytes")
    else:
        print(f"   ✅ Arquivo sem BOM, problema apenas nas quebras de linha")
    
    print(f"\n   💡 Execute 'python pythonsearch.py' para recalcular com correções v2.1.6")

# ═══════════════════════════════════════════════════════════════════════════════
# 🧪 FUNÇÃO DE TESTE v2.1.6
# ═══════════════════════════════════════════════════════════════════════════════

def testar_correcoes():
    """🧪 Testa se as correções estão funcionando v2.1.6"""
    print("\n" + "=" * 80)
    print("🧪 TESTE DE VALIDAÇÃO DAS CORREÇÕES v2.1.6")
    print("=" * 80)
    
    # Teste 1: Simulação de texto com CRLF em arquivo com LF
    print("📝 TESTE 1: Quebras de linha diferentes")
    conteudo_teste = "linha1\nlinha2\nlinha3\ntexto procurado aqui\nlinha5"
    texto_teste = "texto procurado aqui"
    texto_teste_crlf = "texto procurado aqui"  # Simula CRLF
    
    pos = conteudo_teste.find(texto_teste)
    print(f"   Busca direta: {pos}")
    
    # Teste 2: Mapeamento de posições
    print("\n📝 TESTE 2: Mapeamento com normalização")
    conteudo_crlf = "linha1\r\nlinha2\r\nlinha3\r\ntexto procurado aqui\r\nlinha5"
    conteudo_norm = conteudo_crlf.replace('\r\n', '\n')
    pos_norm = conteudo_norm.find(texto_teste)
    
    # Mapeia de volta
    contador = 0
    pos_real = 0
    for i, char in enumerate(conteudo_crlf):
        if contador >= pos_norm:
            pos_real = i
            break
        if char == '\r' and i + 1 < len(conteudo_crlf) and conteudo_crlf[i + 1] == '\n':
            continue
        contador += 1
    
    print(f"   Posição normalizada: {pos_norm}")
    print(f"   Posição real mapeada: {pos_real}")
    print(f"   Texto extraído: {repr(conteudo_crlf[pos_real:pos_real+len(texto_teste)])}")
    
    # Teste 3: Com o arquivo real
    arquivo_path = r"C:\Users\arquivo.js"
    if os.path.exists(arquivo_path):
        print("\n📝 TESTE 3: Arquivo real")
        texto_copiado = obter_texto_copiado()
        if texto_copiado:
            # Testa função calcular_posicoes_precisas
            conteudo = ler_arquivo(arquivo_path)
            posicoes = calcular_posicoes_precisas(conteudo, texto_copiado, "uiRenderer.js", arquivo_path)
            
            if posicoes:
                print(f"   ✅ calcular_posicoes_precisas funcionou!")
                print(f"   📍 Posições: {posicoes['inicio']} até {posicoes['fim']}")
                
                # Valida
                inicio_ajustado = posicoes['inicio']
                fim_ajustado = posicoes['fim']
                
                # Remove offset BOM para validar
                info_encoding = detectar_bom_e_encoding(arquivo_path)
                if info_encoding['has_bom']:
                    inicio_ajustado -= info_encoding['bom_size']
                    fim_ajustado -= info_encoding['bom_size']
                
                texto_extraido = conteudo[inicio_ajustado:fim_ajustado]
                texto_extraido_norm = texto_extraido.replace('\r\n', '\n')
                texto_copiado_norm = texto_copiado.replace('\r\n', '\n')
                
                if texto_extraido_norm == texto_copiado_norm:
                    print(f"   ✅ Validação OK: textos idênticos após normalização")
                else:
                    print(f"   ❌ Validação FALHOU")
                    print(f"      Tamanhos: extraído={len(texto_extraido)}, esperado={len(texto_copiado)}")
            else:
                print(f"   ❌ calcular_posicoes_precisas retornou None")
        else:
            print(f"   ⚠️ Nenhum texto na área de transferência para testar")
    else:
        print(f"\n📝 TESTE 3: Arquivo uiRenderer.js não encontrado")
    
    print("\n✅ Testes concluídos!")

def main():
    """Função principal v2.1.6"""
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                  PYTHON CTRL+C SEARCH & PASTE TOOL v2.1.6                  ║")
    print("║                🚨 CORREÇÃO COMPLETA: Quebras de linha diferentes            ║")
    print("║                🔧 CORREÇÃO: Mapeamento preciso de coordenadas               ║")
    print("║                🆕 CORREÇÃO: Ajuste automático no PASTE                      ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        if comando == 'paste':
            arquivo_especifico = sys.argv[2] if len(sys.argv) > 2 else None
            posicoes = ler_xml_posicoes(arquivo_especifico)
            
            if posicoes:
                print("🔄 CRIANDO BACKUP ANTES DA MODIFICAÇÃO...")
                backup_sucesso = criar_backup_antes_paste(posicoes['caminho'])
                
                if backup_sucesso:
                    print("✅ Backup criado! Prosseguindo com PASTE...\n")
                    if arquivo_especifico:
                        colar_nas_coordenadas(arquivo_especifico)
                    else:
                        colar_nas_coordenadas()
                else:
                    print("❌ ERRO: Não foi possível criar backup. PASTE cancelado por segurança!")
            else:
                print("❌ ERRO: Não foi possível obter informações do arquivo. PASTE cancelado!")
        
        elif comando == 'diagnostico':
            diagnosticar_caso_especifico()
        
        elif comando == 'teste':
            testar_correcoes()
        
        else:
            print(f"❌ Comando desconhecido: {comando}")
            print("📋 Comandos disponíveis:")
            print("   python pythonsearch.py                    # Busca")
            print("   python pythonsearch.py paste              # Paste no melhor resultado")
            print("   python pythonsearch.py paste arquivo.ext  # Paste em arquivo específico")
            print("   python pythonsearch.py diagnostico        # Diagnóstico completo")
            print("   python pythonsearch.py teste              # Testa correções")
    else:
        modo_busca()

if __name__ == "__main__":
    main()
