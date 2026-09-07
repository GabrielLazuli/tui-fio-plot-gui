# FIO Plot Automation

Aplicação gráfica em Python para gerar gráficos a partir de resultados de
benchmark do FIO, reutilizando a biblioteca **fio-plot** como dependência.

A entrada é selecionada por pasta. Cada pasta representa uma execução do
benchmark, normalmente correspondente a um disco ou sistema testado. O
programa procura os arquivos dentro da pasta e os prepara automaticamente
para o tipo de gráfico escolhido. O gráfico é salvo como PNG e aberto ao final
da execução.

## Opções disponíveis

1. **2D Chart - Compare Benchmark Results** - Compara resultados de benchmark
   entre **múltiplos diretórios** (um run por pasta), usando o `resultado.json`
   de cada um.
2. **Line Chart - FIO Log Data** - Gráfico de linha a partir dos **arquivos de
   log** (`*.N.log`) de um único diretório, mostrando read/write ao longo do
   tempo.
3. **Latency Histogram** - Histograma da distribuição de latência a partir do
   `resultado.json` de um único diretório.

As pastas são escolhidas por um diálogo do sistema operacional. Para a
comparação, o programa permite selecionar várias pastas, uma para cada
benchmark. Para os outros gráficos, é selecionada apenas uma pasta.

## Como usar

Requisito: `fio-plot` como dependência.

```bash
pip install -r requirements.txt
python plot_app.py
```

Ao abrir o programa, uma janela apresenta três botões de análise. Escolha o
tipo de gráfico e depois selecione a(s) pasta(s) nas janelas exibidas. Quando possível, o programa detecta
automaticamente `rw`, `iodepth` e `numjobs` a partir do JSON. Se esses valores
não puderem ser detectados, eles serão solicitados em caixas de diálogo. Para workloads
`randrw`, os gráficos baseados no JSON solicitam se devem mostrar leitura ou
escrita; o gráfico de linha mostra as duas métricas.

Para abrir no Windows sem uma janela de terminal, dê duplo clique em
`iniciar_fio_plot.pyw` ou execute pelo `pythonw`:

```powershell
pythonw iniciar_fio_plot.pyw
```

O arquivo PNG recebe o título informado na janela de configuração. Se nenhum título for
informado, o nome padrão é `Resultados-de-Benchmark-FIO.png`. Todos os
gráficos são salvos automaticamente na pasta `assets`, que é criada pelo
programa se necessário.

## Funcionamento da interface

Ao iniciar o programa, a janela principal apresenta três botões:

1. **Comparação 2D** — abre um seletor que permite escolher duas ou mais
   pastas de benchmark.
2. **Gráfico de linha** — abre um seletor para escolher uma pasta com JSON e
   arquivos `.log`.
3. **Histograma de latência** — abre um seletor para escolher uma pasta com
   JSON.

Depois da seleção, o programa detecta os parâmetros do benchmark, solicita
apenas as informações que não estiverem no JSON e pergunta o título e a fonte
do gráfico. Ao final, o PNG é salvo em `assets` e aberto automaticamente. Erros, como uma
pasta sem JSON ou sem logs, são mostrados em uma janela de aviso.

O processamento acontece nesta sequência:

```text
Usuário seleciona uma análise na interface
  ↓
Usuário escolhe a(s) pasta(s) de resultados
  ↓
Python lê o JSON e/ou os arquivos de log
  ↓
O programa prepara os dados para a biblioteca fio-plot
  ↓
fio-plot gera o gráfico PNG
  ↓
O PNG é aberto automaticamente
```

A interface gráfica substitui o menu e as perguntas do terminal. O arquivo
`plot_app.py` continua executando o processamento internamente, mas o usuário
não precisa digitar comandos ou opções. Para executar sem exibir uma janela de
terminal, use `iniciar_fio_plot.pyw` por duplo clique ou com `pythonw`.

## Requisitos dos dados de entrada

Não é necessário criar nenhuma pasta específica dentro deste projeto. Você
pode organizar os resultados em qualquer local e selecioná-los pelo diálogo.
Por exemplo:

```text
resultados/
├── HD_Computador/
│   ├── resultado.json
│   ├── iops_iops.1.log
│   └── iops_iops.2.log
└── NVME_Kingston/
   ├── resultado.json
   ├── iops_iops.1.log
   └── iops_iops.2.log
```

Cada pasta de benchmark pode conter:

- **`resultado.json`** — saída válida do FIO (`fio --output-format=json`) com
  `rw`, `iodepth` e `numjobs` nas job options. Usado na comparação (opção 1) e
  no histograma (opção 3), além de fornecer o workload para os logs (opção 2).
- **Arquivos `*.log`** — logs do FIO por job (formato `time,value,rwt,bs,offset`
  por linha), nomeados como `iops_iops.1.log`, `iops_iops.2.log`, etc. Usados
  no gráfico de linha (opção 2).

O programa procura primeiro um arquivo chamado `resultado.json`. Se ele não
existir, aceita o único arquivo `.json` presente na pasta. Ainda assim,
recomenda-se usar o nome `resultado.json`. O JSON deve ser válido e conter os
dados gerados pelo FIO.

No gráfico de linha, o programa lê o tipo de métrica (`bw`, `iops`, `lat`,
`slat` ou `clat`) do nome do arquivo de log. Se o tipo não puder ser
identificado, ele será solicitado em uma caixa de diálogo. Os logs são copiados para uma pasta
temporária, agregados em intervalos de um segundo e renomeados para o padrão
que o fio-plot espera (`<rw>-iodepth-<N>-numjobs-<M>_<tipo>.<job>.log`). Os
arquivos originais não são modificados.

## Comando para gerar benchmark válido para aplicação (Windows)

Segue um comando para fazer o benchmark através de um arquivo teste no windows:

```bash
fio --name=teste --filename=C:\fio_test.dat --size=4G --rw=randrw --rwmixread=70 --bs=4k --iodepth=32 --direct=1 --numjobs=4 --runtime=60 --group_reporting --output=C:\Users\SeuNome\Desktop\resultado.json --output-format=json --write_iops_log=C:\Users\SeuNome\Desktop\iops
```

- Organize o `resultado.json` e os arquivos `.log` na mesma pasta antes de
  selecioná-la no programa, ou altere os caminhos de `--output` e
  `--write_iops_log` para uma pasta de resultados própria.
- No Windows, use um arquivo de teste em `--filename` para evitar testar
  diretamente um dispositivo ou uma partição. Verifique o comportamento da
  versão do FIO instalada antes de executar benchmarks em dados importantes.

## Preparando resultados em outra máquina

Siga estes passos em cada computador que será testado.

### 1. Instale os programas necessários

Instale o Python, o FIO e a biblioteca do projeto. No PowerShell, dentro da
pasta do projeto, execute:

```powershell
python -m pip install -r requirements.txt
fio --version
```

Se `fio` não for reconhecido, instale o FIO pelo instalador do Windows ou pelo
`winget`:

```powershell
winget install --id fio.fio --source winget
```

Feche e abra o PowerShell novamente após a instalação e confirme com
`fio --version`.

### 2. Crie uma pasta para os resultados

Dentro do projeto, crie uma pasta `resultados` e uma subpasta para cada
benchmark. O nome da subpasta deve identificar a unidade ou a configuração:

```text
resultados/
├── NVME_Maquina_A/
├── SSD_Maquina_B/
└── HD_Maquina_C/
```

Também é possível criar várias pastas na mesma máquina para comparar
configurações diferentes do mesmo dispositivo:

```text
resultados/
├── NVME_numjobs_1/
├── NVME_numjobs_4/
└── NVME_bloco_1M/
```

Nesse segundo caso, a comparação é entre configurações ou cargas de trabalho,
e não entre unidades físicas diferentes.

### 3. Execute o benchmark

Use um arquivo de teste dentro da unidade que será analisada. O FIO cria esse
arquivo automaticamente. Exemplo para a pasta `NVME_Maquina_A`:

```powershell
fio --name=teste --filename="C:\fio_test.dat" --size=1G --rw=randrw --rwmixread=70 --bs=4k --iodepth=32 --direct=1 --numjobs=4 --runtime=30 --group_reporting --thread --output="C:\caminho\do\projeto\resultados\NVME_Maquina_A\resultado.json" --output-format=json --write_iops_log="C:\caminho\do\projeto\resultados\NVME_Maquina_A\iops"
```

Altere `C:\caminho\do\projeto` para o caminho real do projeto nessa
máquina. O parâmetro `--thread` evita o aviso de mutex do FIO no Windows.

O comando acima cria dentro de `NVME_Maquina_A`:

```text
resultado.json
iops_iops.1.log
iops_iops.2.log
iops_iops.3.log
iops_iops.4.log
```

Os quatro logs aparecem porque o comando usa `--numjobs=4`. O arquivo
`fio_test.dat` é apenas a área temporária usada pelo teste e pode ser apagado
depois que o FIO terminar.

### 4. Repita para outras unidades ou configurações

Para testar outra unidade, execute o mesmo comando apontando `--filename` para
um arquivo nessa unidade e altere os caminhos de saída para outra subpasta:

```powershell
fio --name=teste --filename="D:\fio_test.dat" --size=1G --rw=randrw --rwmixread=70 --bs=4k --iodepth=32 --direct=1 --numjobs=4 --runtime=30 --group_reporting --thread --output="C:\caminho\do\projeto\resultados\SSD_Maquina_B\resultado.json" --output-format=json --write_iops_log="C:\caminho\do\projeto\resultados\SSD_Maquina_B\iops"
```

Mantenha iguais os parâmetros `--rw`, `--bs`, `--iodepth`, `--numjobs` e
`--runtime` quando quiser uma comparação justa entre unidades. Para comparar
configurações, altere conscientemente apenas o parâmetro que deseja estudar e
use uma nova subpasta.

### 5. Gere os gráficos

Abra `iniciar_fio_plot.pyw` com duplo clique. Na interface:

- escolha **Comparação 2D** e selecione duas ou mais subpastas com JSON;
- escolha **Gráfico de linha** e selecione uma subpasta com JSON e `.log`;
- escolha **Histograma de latência** e selecione uma subpasta com JSON.

Os PNGs gerados são salvos na pasta `assets` do projeto. Os arquivos de
resultados originais permanecem dentro de suas respectivas subpastas.

## Arquivos temporários

O programa cria automaticamente uma pasta temporária para copiar, renomear e
agregar os dados antes de passá-los ao `fio-plot`. Essa pasta é removida quando
o programa termina. Nenhuma pasta temporária precisa ser criada manualmente.
