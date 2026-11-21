# BT3: Tenkaichi Together

**Dragon History com dois guerreiros de verdade na mesma luta.**

Projeto de cooperativo local para **Dragon Ball Z: Budokai Tenkaichi 3**, executado no **PCSX2**, idealizado e dirigido por **KawEduh**. A base técnica é o [Tag Team Mod, de tehmufti e colaboradores](https://github.com/tehmufti/Budokai-Tenkaichi-3-Tag-Team-Mod-PCSX2-).

> **Em desenvolvimento.** As batalhas cooperativas isoladas já foram testadas. A campanha completa ainda não é uma versão pública pronta para jogar: R3, conclusão das missões e progressão continuam em implementação e verificação.

## O que já foi verificado

- Dois aliados independentes, com controles separados, na luta original contra Raditz.
- Entrada pelos menus originais até Dragon History e seleção da missão; preparação cooperativa nessa luta.
- Preparação dessa luta na mesma execução do emulador, sem recarregar estados entre as etapas, com controles independentes verificados depois.
- A fase continua com o outro jogador controlável quando P1 ou P2 é derrotado, nos testes da fase de Raditz.
- Vida dos aliados e inimigos configurável entre 25% e 400%, preservando a proporção de dano e os personagens derrotados. O padrão dos inimigos é 150%, com mínimo de 60.000 HP.
- Escolha de 1 ou 2 jogadores nos detalhes das batalhas cooperativas isoladas. Com 1 jogador, o parceiro é controlado pela IA.
- Menu próprio com entrada automática, Select sem fechar/reabrir em sequência e Triângulo para retornar ao menu original.
- Adaptador de eventos lê o roteiro carregado em cada capítulo, sem ficar preso ao índice da missão Raditz. Trocas comuns para um aliado já em campo não pedem R3 nem recarregam outro corpo; eventos que combinam troca com golpe roteirizado mantêm a troca nativa para preservar o dano especial e a conclusão. Os capítulos seguintes ainda precisam de validação em jogo.
- Tela de créditos própria, com atribuição ao projeto de origem.

Esses resultados são testes locais de desenvolvimento; não equivalem à certificação de toda a campanha.

## O que está sendo implementado

- Ativação e continuação da campanha completa, preservando os eventos e os saves.
- R3 de troca somente quando existe um aliado na reserva. Um personagem já em combate não é um destino de troca.
- Troca para o primeiro jogador que apertar; transformações sincronizadas quando aplicáveis.
- Pergunta de 1 ou 2 jogadores ao entrar em Dragon History; dificuldade da IA, entradas individuais, em duplas ou simultâneas e inimigos por jogador.
- Menus com arte própria e presets de regras.
- Compatibilidade por perfis de ISO. Mods que alteram código ou scripts precisam de validação; compatibilidade universal não é garantida.

## Tutorial: testar as fontes

Este repositório reúne a extensão em desenvolvimento, não o jogo nem uma ISO modificada.

1. Obtenha sua própria ISO de BT3 e sua própria BIOS de PS2.
2. Instale e configure a [base Tag Team Mod 14.6](https://github.com/tehmufti/Budokai-Tenkaichi-3-Tag-Team-Mod-PCSX2-/releases/tag/v0.1.0-beta.14.6), seguindo o tutorial do autor. Confirme primeiro que ela abre normalmente.
3. Feche o PCSX2 e faça uma cópia da instalação de desenvolvimento.
4. Copie os arquivos de `extension/` para a pasta `tools/` do jogo nessa cópia. Eles dependem dos demais módulos da base 14.6; não funcionam sozinhos.
5. Em `mod-settings.json`, mantenha as configurações existentes e acrescente `"fullcoop_interface": true`.
6. Copie os cenários de `missions/FullCoop/` para a mesma pasta relativa da instalação.
7. Abra o launcher da base. No menu do mod, escolha as batalhas cooperativas e um cenário de teste. Nos detalhes, use esquerda/direita para escolher 1 ou 2 jogadores antes de confirmar.

O menu próprio abre automaticamente. Triângulo volta ao menu original; Select abre o menu próprio a partir dele. Para as missões cooperativas preparadas, os ajustes de HP ficam em **Configurações → História cooperativa** e são aplicados na preparação seguinte.

**Entrar em Dragon History pelo launcher comum ainda não ativa automaticamente uma campanha cooperativa completa.** Os scripts internos de diagnóstico não são um atalho de jogo nem um instalador para usuários finais. Um tutorial da versão jogável será publicado junto da versão que concluir essa integração.

### Controles

Use dois controles configurados como **Porta 1** e **Porta 2** no PCSX2. A extensão preserva os mapeamentos existentes.

Na instalação local de desenvolvimento também há o perfil de teclado:

| Ação | P1 | P2 |
|---|---|---|
| Movimento | WASD | IJKL |
| Ataque | V | Num4 |
| Ki | Z | Num8 |
| Defesa | X | Num6 |
| Confirmar | C | Num2 |
| Start | Enter | Enter numérico |

Esse perfil de teclado não é imposto pela cópia das fontes; configure as portas no emulador conforme seus dispositivos.

## Créditos

| Participação | Crédito |
|---|---|
| Projeto, direção e idealização | **KawEduh** |
| Base técnica de combate simultâneo | **[Tag Team Mod — tehmufti e colaboradores](https://github.com/tehmufti/Budokai-Tenkaichi-3-Tag-Team-Mod-PCSX2-)** |
| Referência para leitura dos scripts GSC | [Documentação de Tenkaichi3Decomp](https://github.com/z3xox/Tenkaichi3Decomp/blob/main/docs/systems/script.md), consultada para a análise do formato |
| Jogo original | Créditos e direitos dos respectivos criadores e titulares de Dragon Ball Z: Budokai Tenkaichi 3 |

O projeto reaproveita sistemas e código da base, sem utilizar seu logo ou suas texturas de apresentação. Os retratos e recursos originais são lidos da ISO fornecida pelo jogador. A arte nova de apresentação pertence ao desenvolvimento desta extensão.

## Licença e conteúdo

As alterações derivadas da base seguem **GPL-3.0**. Consulte [LICENSE](LICENSE) e [UPSTREAM-NOTICE](UPSTREAM-NOTICE).

O repositório não inclui ISO, BIOS, saves, dumps de RAM, arquivos do jogo extraídos, prompts particulares, logs ou arquivos `.txt` de trabalho.

Base de desenvolvimento: `v0.1.0-beta.14.6`, commit `3a7cc4e563f46561619d74c487cf8e1d4d267c6e`.
