<?php
/*
 *     E-cidade Software Publico para Gestao Municipal
 *  Copyright (C) 2009  DBSeller Servicos de Informatica
 *                            www.dbseller.com.br
 *                         e-cidade@dbseller.com.br
 *
 *  Este programa e software livre; voce pode redistribui-lo e/ou
 *  modifica-lo sob os termos da Licenca Publica Geral GNU, conforme
 *  publicada pela Free Software Foundation; tanto a versao 2 da
 *  Licenca como (a seu criterio) qualquer versao mais nova.
 *
 *  Este programa e distribuido na expectativa de ser util, mas SEM
 *  QUALQUER GARANTIA; sem mesmo a garantia implicita de
 *  COMERCIALIZACAO ou de ADEQUACAO A QUALQUER PROPOSITO EM
 *  PARTICULAR. Consulte a Licenca Publica Geral GNU para obter mais
 *  detalhes.
 *
 *  Voce deve ter recebido uma copia da Licenca Publica Geral GNU
 *  junto com este programa; se nao, escreva para a Free Software
 *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
 *  02111-1307, USA.
 *
 *  Copia da licenca no diretorio licenca/licenca_en.txt
 *                                licenca/licenca_pt.txt
 */

namespace App\Domain\Financeiro\Planejamento\Relatorios;

use PhpOffice\PhpSpreadsheet\Cell\Coordinate;
use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Style\Alignment;
use PhpOffice\PhpSpreadsheet\Style\Border;
use PhpOffice\PhpSpreadsheet\Style\Borders;
use PhpOffice\PhpSpreadsheet\Worksheet\Worksheet;
use PhpOffice\PhpSpreadsheet\Writer\Xlsx;
use PhpOffice\PhpSpreadsheet\Style\Color;

/**
 * Class ProgramaGestaoCsv
 * @package App\Domain\Financeiro\Planejamento\Relatorios
 */
class ProgramaGestaoXls
{
    /**
     * @var array
     */
    private $dados = [];
    /**
     * @var string
     */
    private $periodo;
    /**
     * @var array
     */
    private $exercicios = [];
    /**
     * @var int|void
     */
    private $numeroExercicios;

    /**
     * @var Spreadsheet
     */
    private $spreadsheet;
    /**
     * @var Worksheet
     */
    private $sheet;

    private $defaulFillColor = 'B3B3B4';

    /**
     * controle da linha impressa
     * @var int
     */
    private $linha = 1;

    private $cells = [
        1 => 'A',
        2 => 'B',
        3 => 'C',
        4 => 'D',
        5 => 'E',
        6 => 'F',
        7 => 'G',
        8 => 'H',
        9 => 'I',
        10 => 'J'
    ];


    public function __construct()
    {
        $this->spreadsheet = new Spreadsheet();
        $this->sheet = $this->spreadsheet->getActiveSheet();
        $this->sheet->setTitle('Temático');
    }

    /**
     * @param array $dados
     */
    public function setDados(array $dados)
    {
        $this->dados = $dados;
        $planejamento = $this->dados['planejamento'];
        $this->periodo = sprintf('%s a %s', $planejamento['pl2_ano_inicial'], $planejamento['pl2_ano_final']);
        $this->exercicios = $planejamento['exercicios'];
        $this->numeroExercicios = count($this->exercicios);
    }

    public function emitir()
    {
//        $filename = sprintf('tmp/programae-gestao-%s.xlsx', time());
        $filename = sprintf('tmp/programae-gestao.xlsx');

        $this->imprimePlanejamento();
        $this->imprimeProgramas();

        $this->sheet->getColumnDimension('A')->setAutoSize(true);
        $this->sheet->getColumnDimension('B')->setAutoSize(true);
        $this->sheet->getColumnDimension('C')->setAutoSize(true);
        $this->sheet->getColumnDimension('D')->setAutoSize(true);
        $this->sheet->getColumnDimension('E')->setAutoSize(true);
        $this->sheet->getColumnDimension('F')->setAutoSize(true);

        $writer = new Xlsx($this->spreadsheet);
        $writer->save($filename);

        return [
            'xls' => $filename,
            'xlsLinkExterno' => ECIDADE_REQUEST_PATH . $filename
        ];
    }

    private function imprimePlanejamento()
    {
        $this->mergeCellsByColumnAndRow(1, $this->linha, 16, $this->linha);
        $style = $this->getStyleByColumnAndRow(1, $this->linha, 1, $this->linha);
        $this->setFontColor($style);
        $this->setBorder($style);
        $this->setBold($style);

        $titulo = sprintf('%s  %s', $this->dados['planejamento']['pl2_titulo'], $this->periodo);

        $this->sheet->setCellValue("A1", $titulo);
        $this->linha++;
    }

    private function tituloPrograma()
    {
        $columnIndexEnd = 2 + ($this->numeroExercicios);
        $coordinate = "A{$this->linha}";
        $this->mergeCellsByColumnAndRow(1, $this->linha, $columnIndexEnd, $this->linha);

        $this->sheet->setCellValue($coordinate, 'Programas de Gestão e Manutenção ao Estado');
        $style = $this->getStyleByColumnAndRow(1, $this->linha, $columnIndexEnd, $this->linha);
        $this->setBold($style);
        $this->setBorder($style);
        $this->linha++;
    }

    /**
     * @throws \PhpOffice\PhpSpreadsheet\Exception
     */
    private function cabecalhoPrograma()
    {
        $columnIndexEnd = 2 + ($this->numeroExercicios);
        $linhaInicio = $this->linha;

        $this->mergeCellsByColumnAndRow(1, $this->linha, 2, $this->linha);
        $this->mergeCellsByColumnAndRow(3, $this->linha, $columnIndexEnd, $this->linha);
        $this->setCellValueByColumnAndRow(1, $this->linha, '1. Descrição do Programa');
        $this->setCellValueByColumnAndRow(3, $this->linha, '1.1 Valor do programa');
        $this->linha++;

        $colunas = array_merge(['Código', 'Título'], $this->exercicios);
        $this->adicionaColunas($colunas);


        $style = $this->getStyleByColumnAndRow(1, $linhaInicio, $columnIndexEnd, $this->linha);
        $this->setBold($style);
        $this->setBorder($style);
        $this->setAlign($style, Alignment::HORIZONTAL_LEFT, Alignment::VERTICAL_CENTER);
        $this->linha++;
    }

    private function imprimeProgramas()
    {
        $this->tituloPrograma();
        $this->cabecalhoPrograma();
        foreach ($this->dados['programas'] as $programa) {
            $valores = [];
            foreach ($programa['valores'] as $valor) {
                $valorFormatado = $valor['pl10_valor'];
                $valores [] = $valorFormatado;
            }

            $colunas = array_merge(["" . $programa['formatado'], utf8_encode($programa['o54_descr'])], $valores);

            foreach ($colunas as $key => $coluna) {
                $columnIndex = $key + 1;
                $this->setCellValueByColumnAndRow($columnIndex, $this->linha, $coluna);
            }
            $this->linha++;

            $this->imprimeOrgaos($programa['orgaos']);
            $this->imprimeIniciativas($programa['iniciativas']);
            $this->linha++;
            $this->cabecalhoPrograma();
        }
    }

    private function cabecalhoIniciativa()
    {
        $linhaInicio = $this->linha;
        //merge da celula 1.2 - Iniciativas
        $this->mergeCellsByColumnAndRow(1, $this->linha, 2, ($this->linha + 1));
        //merge da celula Regionalização
        $this->mergeCellsByColumnAndRow(3, $this->linha, 3, ($this->linha + 2));
        //merge da celula Produto
        $this->mergeCellsByColumnAndRow(4, $this->linha, 4, ($this->linha + 2));
        //merge da celula Metas Financeiras
        $columnIndexFinalMetaFinanceira = 4 + $this->numeroExercicios;
        $columnIndexInicioMetaFinanceira = 5;
        $this->mergeCellsByColumnAndRow(
            $columnIndexInicioMetaFinanceira,
            $this->linha,
            $columnIndexFinalMetaFinanceira,
            ($this->linha + 1)
        );
        //merge da celula Metas Física
        $columnIndexInicialMetaFisica = $columnIndexFinalMetaFinanceira + 1;

        $columnIndexFinalMetaFisica = $columnIndexFinalMetaFinanceira + ($this->numeroExercicios * 2);
        $this->mergeCellsByColumnAndRow(
            $columnIndexInicialMetaFisica,
            $this->linha,
            $columnIndexFinalMetaFisica,
            $this->linha
        );

        // priemira linha
        $this->setCellValueByColumnAndRow(1, $this->linha, '1.3 Iniciativas');
        $this->setCellValueByColumnAndRow(3, $this->linha, 'Regionalização');
        $this->setCellValueByColumnAndRow(4, $this->linha, 'Produto');
        $this->setCellValueByColumnAndRow($columnIndexInicioMetaFinanceira, $this->linha, 'Metas Financeiras');
        $this->setCellValueByColumnAndRow($columnIndexInicialMetaFisica, $this->linha, 'Metas Física');

        // segunda linha
        $this->linha++;
        $inicioMerge = $columnIndexInicialMetaFisica;
        foreach ($this->exercicios as $exercicio) {
            $this->mergeCellsByColumnAndRow($inicioMerge, $this->linha, $inicioMerge + 1, $this->linha);
            $this->setCellValueByColumnAndRow($inicioMerge, $this->linha, $exercicio);
            $inicioMerge += 2;
        }

        // terceira linha
        $this->linha++;
        $this->setCellValueByColumnAndRow(1, $this->linha, 'Código');
        $this->setCellValueByColumnAndRow(2, $this->linha, 'Descrição');
        $inicio = $columnIndexInicioMetaFinanceira;
        foreach ($this->exercicios as $exercicio) {
            $this->setCellValueByColumnAndRow($inicio, $this->linha, $exercicio);
            $inicio++;
        }
        $inicio = $columnIndexInicialMetaFisica;
        foreach ($this->exercicios as $exercicio) {
            $this->setCellValueByColumnAndRow($inicio, $this->linha, 'Unidade');
            $inicio++;
            $this->setCellValueByColumnAndRow($inicio, $this->linha, 'Valor');
            $inicio++;
        }
        $style = $this->getStyleByColumnAndRow(1, $linhaInicio, $columnIndexFinalMetaFisica, $this->linha);

        $this->setBold($style);
        $this->setBorder($style);
        $this->setAlign($style, Alignment::HORIZONTAL_LEFT, Alignment::VERTICAL_CENTER);

        $this->linha++;
    }

    private function imprimeIniciativas($iniciativas)
    {
        $this->cabecalhoIniciativa();

        foreach ($iniciativas as $iniciativa) {
            $produto = $iniciativa['descricao_produto'];
            $regionalizacao = collect($iniciativa['regionalizacoes'])->implode('o11_descricao', ', ');

            $colunas = [
                ''.$iniciativa['acao'],
                utf8_encode($iniciativa['descricao_acao']),
                utf8_encode($regionalizacao),
                utf8_encode($produto),
            ];

            if (count($iniciativa['metas'])) {
                $metaFinacaneira = [];
                $metaFisica = [];
                foreach ($iniciativa['metas'] as $meta) {
                    $metaFinacaneira[] = $meta['meta_financeira'];
                    $metaFisica[] = $meta['unidade'];
                    $metaFisica[] = $meta['meta_fisica'];
                }

                $colunas = array_merge($colunas, $metaFinacaneira, $metaFisica);
            }

            $this->adicionaColunas($colunas);
            $this->linha ++;
        }
    }

    private function imprimeOrgaos($orgaos)
    {
        $this->cabecalhOrgao();

        foreach ($orgaos as $orgao) {
            $colunas = array_merge(["" . $orgao['formatado'], utf8_encode($orgao['descricao'])]);

            foreach ($colunas as $key => $coluna) {
                $columnIndex = $key + 1;
                $this->setCellValueByColumnAndRow($columnIndex, $this->linha, $coluna);
            }
            $this->linha++;
        }
        $this->linha++;
    }

    private function cabecalhOrgao()
    {
        $columnIndexEnd = 2 + ($this->numeroExercicios);
        $coordinate = "A{$this->linha}";
        $this->mergeCellsByColumnAndRow(1, $this->linha, $columnIndexEnd, $this->linha);
        $this->sheet->setCellValue($coordinate, '1.2 Orgãos');

        $style = $this->getStyleByColumnAndRow(1, $this->linha, $columnIndexEnd, $this->linha);
        $this->setBold($style);
        $this->setBorder($style);
        $this->linha++;
    }
    /**
     * @param array $colunas
     */
    private function adicionaColunas(array $colunas)
    {
        foreach ($colunas as $key => $coluna) {
            $columnIndex = $key + 1;
            $this->setCellValueByColumnAndRow($columnIndex, $this->linha, $coluna);
        }
    }

    /**
     * Os metodos *ByColumnAndRow da planilha sairam do PhpSpreadsheet 2. Estes tres fazem o que os da 1.8.2 faziam:
     * montam a coordenada com Coordinate::stringFromColumnIndex() e chamam o metodo por coordenada.
     */
    private function setCellValueByColumnAndRow($columnIndex, $row, $value)
    {
        $this->sheet->setCellValue(Coordinate::stringFromColumnIndex($columnIndex) . $row, $value);
    }

    private function mergeCellsByColumnAndRow($columnIndex1, $row1, $columnIndex2, $row2)
    {
        $this->sheet->mergeCells(
            Coordinate::stringFromColumnIndex($columnIndex1) . $row1 . ':' . Coordinate::stringFromColumnIndex($columnIndex2) . $row2
        );
    }

    private function getStyleByColumnAndRow($columnIndex1, $row1, $columnIndex2, $row2)
    {
        return $this->sheet->getStyle(
            Coordinate::stringFromColumnIndex($columnIndex1) . $row1 . ':' . Coordinate::stringFromColumnIndex($columnIndex2) . $row2
        );
    }

    /**
     * @param \PhpOffice\PhpSpreadsheet\Style\Style $style
     * @throws \PhpOffice\PhpSpreadsheet\Exception
     */
    private function setBorder(\PhpOffice\PhpSpreadsheet\Style\Style $style)
    {
        $style->getBorders()
            ->getAllBorders()
            ->setBorderStyle(Border::BORDER_THIN);
    }

    /**
     * @param \PhpOffice\PhpSpreadsheet\Style\Style $style
     */
    private function setBold(\PhpOffice\PhpSpreadsheet\Style\Style $style)
    {
        $style->getFont()->setBold(true);
    }

    /**
     * @param \PhpOffice\PhpSpreadsheet\Style\Style $style
     */
    private function setFillCollor(\PhpOffice\PhpSpreadsheet\Style\Style $style, $color = null)
    {
        if (is_null($color)) {
            $color = $this->defaulFillColor;
        }

        $style->getFill()
            ->setFillType(\PhpOffice\PhpSpreadsheet\Style\Fill::FILL_SOLID)
            ->getStartColor()
            ->setARGB($color);
    }

    /**
     * @param \PhpOffice\PhpSpreadsheet\Style\Style $style
     * @param string $color
     */
    private function setFontColor(\PhpOffice\PhpSpreadsheet\Style\Style $style, $color = '000000')
    {
        $style->getFont()->getColor()->setARGB($color);
    }


    /**
     * @param \PhpOffice\PhpSpreadsheet\Style\Style $style
     * @param $horizontal
     * @param $verical
     */
    private function setAlign(\PhpOffice\PhpSpreadsheet\Style\Style $style, $horizontal, $verical)
    {
        $style->getAlignment()->setHorizontal(Alignment::HORIZONTAL_LEFT);
        $style->getAlignment()->setVertical(Alignment::VERTICAL_CENTER);
    }
}
