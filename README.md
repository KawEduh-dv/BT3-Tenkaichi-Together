# BT3: Tenkaichi Together

**Dragon History com dois guerreiros de verdade na mesma luta.**

Projeto de cooperativo local para **Dragon Ball Z: Budokai Tenkaichi 3**, executado no **PCSX2**, idealizado e dirigido por **KawEduh**. A base técnica é o [Tag Team Mod, de tehmufti e colaboradores](https://github.com/tehmufti/Budokai-Tenkaichi-3-Tag-Team-Mod-PCSX2-).

> **Em desenvolvimento.** As batalhas cooperativas isoladas já foram testadas. A campanha completa ainda não é uma versão pública pronta para jogar: R3, conclusão das missões e progressão continuam em implementação e verificação.

## O que já foi verificado

- Dois aliados independentes, com controles separados, na luta original contra Raditz.
- Entrada pelos menus originais até Dragon History e seleção da missão; preparação cooperativa nessa luta.
- A fase continua com o outro jogador controlável quando P1 ou P2 é derrotado, nos testes da fase de Raditz.
- Aumento de HP dos inimigos: a configuração inicial usa 150% do HP original, com mínimo de 60.000.
- Tela de créditos própria, com atribuição ao projeto de origem.

Esses resultados são testes locais de desenvolvimento; não equivalem à certificação de toda a campanha.

## O que está sendo implementado

- Ativação e continuação da campanha completa, preservando os eventos e os saves.
- R3 de troca somente quando existe um aliado na reserva. Um personagem já em combate não é um destino de troca.
- Troca para o primeiro jogador que apertar; transformações sincronizadas quando aplicáveis.
- Configurações de HP, dificuldade da IA, entradas individuais, em duplas ou simultâneas e inimigos por jogador.
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
7. Abra o launcher da base. No menu do mod, escolha as batalhas cooperativas e um cenário de teste, com dois jogadores na mesma equipe.

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
| Jogo original | Créditos e direitos dos respectivos criadores e titulares de Dragon Ball Z: Budokai Tenkaichi 3 |

O projeto reaproveita sistemas e código da base, sem utilizar seu logo ou suas texturas de apresentação. Os retratos e recursos originais são lidos da ISO fornecida pelo jogador. A arte nova de apresentação pertence ao desenvolvimento desta extensão.

## Licença e conteúdo

As alterações derivadas da base seguem **GPL-3.0**. Consulte [LICENSE](LICENSE) e [UPSTREAM-NOTICE](UPSTREAM-NOTICE).

O repositório não inclui ISO, BIOS, saves, dumps de RAM, arquivos do jogo extraídos, prompts particulares, logs ou arquivos `.txt` de trabalho.

Base de desenvolvimento: `v0.1.0-beta.14.6`, commit `3a7cc4e563f46561619d74c487cf8e1d4d267c6e`.
