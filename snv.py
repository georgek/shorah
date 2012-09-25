#!/usr/bin/python

# Copyright 2007-2012
# Niko Beerenwinkel,
# Nicholas Eriksson,
# Moritz Gerstung,
# Lukas Geyrhofer,
# Osvaldo Zagordi,
# Kerensa McElroy,
# ETH Zurich

# This file is part of ShoRAH.
# ShoRAH is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# ShoRAH is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with ShoRAH.  If not, see <http://www.gnu.org/licenses/>.


'''
    ------------
    Output:
    a file of raw snvs, parsed from the directory support,
    and a directory containing snvs resulting from strand
    bias tests with different sigma values
    ------------
'''

import sys
import os
import gzip
import shutil
import glob


def segments(incr):
    """How many times is a window segment covered?
       Read it from coverage.txt generated by b2w
    """
    segCov1 = {}
    try:
        infile = open('coverage.txt')
    except IOError:
        sys.exit('Coverage file generated by b2w not found.')
    for f in infile:
        # window_file, reference, begin, end, value
        w, c, b, e, v = f.rstrip().split('\t')
        b = int(b)
        del([w, e, v])
        segs = [c + str(b), c + str(b + incr), c + str(b + incr * 2)]
        for i1, s1 in enumerate(segs):
            if s1 in segCov1:
                segCov1[s1][i1] = 1
            else:
                segCov1[s1] = [0, 0, 0]
                segCov1[s1][i1] = 1
    infile.close()

    return segCov1


def parseWindow(line, ref1):
    """SNVs from individual support files, getSNV will build
        the consensus SNVs
    """
    ind = {'A': '.0', 'T': '.1', 'G': '.2', 'C': '.3',
           'a': '.0', 't': '.1', 'g': '.2', 'c': '.3', '-': '.4'}
    snp = {}
    reads = 0.0
    winFile, chrom, beg, end, cov = line.rstrip().split('\t')
    del([winFile, cov])
    filename = 'w-%s-%s-%s.reads-support.fas' % (chrom, beg, end)

    try:
        window = open(filename)
    except IOError:
        window = open('support/' + filename)
    except IOError:
        window = gzip.open('support/' + filename + '.gz')
    except IOError:
        window = gzip.open(filename + '.gz')
    b = int(beg) - 1
    e = int(end)
    refSlice = ref1[chrom][b:e]
    # This below could be done in Biopython more easily
    head = window.readline()  # support sequence: id and description
    seq = window.readline()  # support sequence: nucleotides
    while head and seq:
        post, av = head.rstrip().split(' ')
        post = float(post.split('=')[-1])
        av = float(av.split('=')[-1])
        if post >= 0.9:
            reads += av
            seq = seq.upper()
            pos = int(beg)
            for i2, v in enumerate(refSlice):
                if v != seq[i2]:
                    id2 = float(str(pos) + ind[seq[i2]])
                    if id2 in snp:
                        snp[id2][4] += av
                        snp[id2][5] += post * av
                    else:
                        snp[id2] = [chrom, pos, v, seq[i2], av, post * av]
                pos += 1
        head = window.readline()
        seq = window.readline()
    key = snp.keys()
    for k in key:
        snp[k][5] /= float(snp[k][4])
        snp[k][4] /= reads
    return snp


def getSNV(ref, segCov, incr):
    """Parses SNV from all windows and output the dictionary with all the
    information
    """
    snpD = {}
    try:
        cov_file = open('coverage.txt')
    except IOError:
        sys.exit('Coverage file generated by b2w not found')
    for f in cov_file:
        snp = parseWindow(f, ref)
        beg = int(f.split('\t')[2])
        key = snp.keys()
        key.sort()
        for k in key:
            chrom, p, rf, var, av, post = snp[k]
            if k in snpD:
                if p < (beg + incr):
                    snpD[k][4][2] = av
                    snpD[k][5][2] = post
                elif p < (beg + incr * 2):
                    snpD[k][4][1] = av
                    snpD[k][5][1] = post
                else:
                    snpD[k][4][0] = av
                    snpD[k][5][0] = post
            else:
                if p < (beg + incr):
                    cov = segCov[chrom + str(beg)]
                    if cov == [1, 1, 1]:
                        snpD[k] = [chrom, p, rf, var, ['-', '-', av],
                                  ['-', '-', post]]
                    elif cov == [1, 0, 0]:
                        snpD[k] = [chrom, p, rf, var, ['*', '*', av],
                                   ['*', '*', post]]
                    elif cov == [1, 1, 0]:
                        snpD[k] = [chrom, p, rf, var, ['*', '-', av],
                                   ['*', '-', post]]
                elif p < (beg + incr * 2):
                    cov = segCov[chrom + str(beg + incr)]
                    if cov == [1, 1, 1]:
                        snpD[k] = [chrom, p, rf, var, ['-', av, '-'],
                                  ['-', post, '-']]
                    elif cov == [1, 1, 0]:
                        snpD[k] = [chrom, p, rf, var, ['*', av, '-'],
                                  ['*', post, '-']]
                    elif cov == [0, 1, 1]:
                        snpD[k] = [chrom, p, rf, var, ['-', av, '*'],
                                  ['-', post, '*']]
                    elif cov == [0, 1, 0]:
                        snpD[k] = [chrom, p, rf, var, ['*', av, '*'],
                                  ['*', post, '*']]
                else:
                    cov = segCov[chrom + str(beg + incr * 2)]
                    if cov == [1, 1, 1]:
                        snpD[k] = [chrom, p, rf, var, [av, '-', '-'],
                                  [post, '-', '-']]
                    elif cov == [0, 1, 1]:
                        snpD[k] = [chrom, p, rf, var, [av, '-', '*'],
                                  [post, '-', '*']]
                    elif cov == [0, 0, 1]:
                        snpD[k] = [chrom, p, rf, var, [av, '*', '*'],
                                  [post, '*', '*']]

    return snpD


def printRaw(snpD2):
    """Print the SNPs as they are obtained from the support files produced
        with shorah (raw calls). raw_snv.txt has all of them, SNV.txt only
        those covered by at least two windows.
    """
    key = snpD2.keys()
    key.sort()
    out = open('raw_snv.txt', 'w')
    out1 = open('SNV.txt', 'w')
    header_row_p = ['Chromosome', 'Pos', 'Ref', 'Var', 'Frq1', 'Frq2', 'Frq3',
                    'Pst1', 'Pst2', 'Pst3']
    out.write('\t'.join(header_row_p) + '\n')
    out1.write('\t'.join(header_row_p) + '\n')
    for k in key:
        out.write(snpD2[k][0] + '\t' + str(snpD2[k][1]) + '\t' + snpD2[k][2] +
                  '\t' + snpD2[k][3])
        count = 0
        for i in range(3):
            if type(snpD2[k][4][i]) == float:
                freq = '\t%.4f' % snpD2[k][4][i]
                count += 1
            else:
                freq = '\t' + snpD2[k][4][i]
            out.write(freq)
        for i in range(3):
            if type(snpD2[k][5][i]) == float:
                post = '\t%.4f' % snpD2[k][5][i]
            else:
                post = '\t' + snpD2[k][5][i]
            out.write(post)
        out.write('\n')
        if count >= 2:
            out1.write(snpD2[k][0] + '\t' + str(snpD2[k][1]) + '\t' +
                       snpD2[k][2] + '\t' + snpD2[k][3])
            for i in range(3):
                if type(snpD2[k][4][i]) == float:
                    freq = '\t%.4f' % snpD2[k][4][i]
                else:
                    freq = '\t' + snpD2[k][4][i]
                out1.write(freq)
            for i in range(3):
                if type(snpD2[k][5][i]) == float:
                    post = '\t%.4f' % snpD2[k][5][i]
                else:
                    post = '\t' + snpD2[k][5][i]
                out1.write(post)
            out1.write('\n')
    out.close()
    out1.close()


def sb_filter(in_bam, sigma):

    """run strand bias filter calling the external program 'fil'
    """
    import subprocess
    dn = os.path.dirname(__file__)
    my_prog = os.path.join(dn, 'fil')
    my_arg = ' -b ' + in_bam + ' -v ' + str(sigma)
    retcode = subprocess.call(my_prog + my_arg, shell=True)
    return retcode


def BH(p_vals, n):
    """performs Benjamini Hochberg procedure, returning q-vals'
       you can also see http://bit.ly/QkTflz
    """
    q_vals_l = []
    prev_bh = 0
    for i, p in enumerate(p_vals):
        # Sometimes this correction can give values greater than 1,
        # so we set those values at 1
        bh = p[0] * n / (i + 1)
        bh = min(bh, 1)
        # To preserve monotonicity in the values, we take the
        # maximum of the previous value or this one, so that we
        # don't yield a value less than the previous.
        bh = max(bh, prev_bh)
        prev_bh = bh
        q_vals_l.append((bh, p[1]))
    return q_vals_l


def main(reference='', bam_file='', sigma=0.01, increment=1):
    '''main code
    '''
    import csv
    from Bio import SeqIO

    ref_m = dict([[s.id, s.seq.tostring().upper()]
                 for s in SeqIO.parse(reference, 'fasta')])

    # number of windows per segment
    segCov_m = segments(increment)

    # snpD_m is the file with the 'consensus' SNVs (from different windows)
    if not os.path.isfile('snv/SNV.txt'):
        snpD_m = getSNV(ref_m, segCov_m, increment)
        printRaw(snpD_m)
    else:
        shutil.move('snv/SNV.txt', './')

    #run strand bias filter, output in SNVs_%sigma.txt
    retcode_m = sb_filter(bam_file, sigma)
    if retcode_m is not 0:
        sys.exit()

    # parse the p values from SNVs*txt file
    snpFile = glob.glob('SNVs*.txt')[0]  # takes the first file only!!!
    snvs = open(snpFile)
    write_list = []
    p_vals_m = []
    x = 0
    for s in snvs:
        parts = s.rstrip().split('\t')
        p1 = parts[-1]
        p_vals_m.append((float(p1), x))
        write_list.append(s.rstrip().split('\t'))
        x += 1
    snvs.close()

    # sort p values, correct with Benjamini Hochberg and write to file
    p_vals_m.sort()
    q_vals = BH(p_vals_m, len(p_vals_m))
    csv_file = '.'.join(snpFile.split('.')[:-1]) + '_final.csv'
    with open(csv_file, 'wb') as cf:
        writer = csv.writer(cf)
        header_row = ['Chromosome', 'Pos', 'Ref', 'Var', 'Frq1', 'Frq2',
                      'Frq3', 'Pst1', 'Pst2', 'Pst3', 'Fvar', 'Rvar',
                      'Ftot', 'Rtot', 'Pval', 'Qval']
        writer.writerow(header_row)
        for q, i3 in q_vals:
            write_list[i3].append(q)
        # only print when q >= 5%
        for wl in write_list:
            if wl[-1] >= 0.05:
                writer.writerow(wl)


if __name__ == "__main__":
    import optparse

    # parse command line
    optparser = optparse.OptionParser()
    opts = main.func_defaults  # set the defaults (see http://bit.ly/2hCTQl)

    optparser.add_option("-r", "--ref", default=opts[0], type="string",
                         dest="r", help="reference file")

    optparser.add_option("-b", "--bam", default=opts[1], type="string",
                         dest="b", help="sorted bam format alignment file")

    optparser.add_option("-s", "--sigma", default=opts[2], type="float",
                         dest="s", help="value of sigma to use when calling\
                         SNVs <%default>")

    optparser.add_option("-i", "--increment", default=opts[3], type="int",
                         dest="i", help="value of increment to use when\
                         calling SNVs <%default>")

    (options, args) = optparser.parse_args()

    main(*args, **vars(opts))
