#//////////////////////////////////////////////////////////////////////////#
#                                                                          #
#   Copyright (C) 2019 by David B. Blumenthal                              #
#                                                                          #
#   This file is part of EpiGEN.                                           #
#                                                                          #
#   EpiGEN is free software: you can redistribute it and/or modify         #
#   it under the terms of the GNU General Public License as published by   #
#   the Free Software Foundation, either version 3 of the License, or      #
#   (at your option) any later version.                                    #
#                                                                          #
#   EpiGEN is distributed in the hope that it will be useful,              #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the           #
#   GNU General Public License for more details.                           #
#                                                                          #
#   You should have received a copy of the GNU General Public License      #
#   along with EpiGEN. If not, see <http://www.gnu.org/licenses/>.         #
#                                                                          #
#//////////////////////////////////////////////////////////////////////////#

"""Contains definition of DataSimulator class."""

import numpy as np
import json
import bz2
import os.path
from .extensional_model import ExtensionalModel
from .parametrized_model import ParametrizedModel
from scipy import stats

class DataSimulator(object):
    """Simulates epistasis data given a pre-generated genotype corpus.
    
    This class is employed by the script simulate_data.py.
    Not intended for use outside of this script.
    Expects to be imported from EpiGEN's root directory.
    
    Attributes:
        genotype (numpy.array): A numpy.array with entries from range(3) whose rows represent SNPs and whose
            columns represent individuals.
        snps (list of (list of str)): A list with one entry for each row of self.genotype. The entries provide information 
            about the corresponding SNP.
        mafs (numpy.array): A numpy.array of floats representing the MAFs of all rows of self.genotype.
        cum_mafs (list of (float,int)): A list of pairs of the form (MAF,count) representing the cumulative MAF distribution.
        model (ExtensionalModel/ParametrizedModel): The epistasis model.
        sim_id (int): An integer that represents the ID of the generated data.
        corpus_id (int): An integer that represents the ID of the genotype corpus on top of which 
            the data should be simulated.
        pop (str): A string representing the HAPMAP3 population for which the selected genotype corpus was 
            generated.
        num_snps (int): The number of SNPs in the simulated data.
        num_inds (int): The number of individuals in the simulated data.
        total_num_snps (int): The number of SNPs in the selected genotype corpus.
        total_num_inds (int): The number of individuals in the selected genotype corpus.
        biased_distr (list of float): Parameters of biased observed phenotype distribution. If empty, no observation bias is applied.
        phenotype (numpy.array): A numpy.array that stores the generated phenotypes.
        disease_snps (list of int): A list of positions of the selected disease SNPs in self.snps and self.genotype.
        noise_maf_range (float,float): A tuple of floats between 0 and 1 that specifies the range of acceptable MAFs for the selected noise SNPs.
        disease_maf_range (float,float): A tuple of floats between 0 and 1 that specifies the range of acceptable MAFs for the selected disease SNPs.
        epsilon (float): A small positive real used for comparing floats.
        compress (bool): If True, the simulated data is compressed.
    """


    def __init__(self, sim_id, corpus_id, pop, model, num_snps, num_inds, disease_snps, biased_distr, noise_maf_range, disease_maf_range, seed, compress):
        """Initialized DataSimulator.
        
        Args:
            sim_id (int): An integer that represents the ID of the generated data.
            corpus_id (int): An integer that represents the ID of the genotype corpus on top of which 
                the data should be simulated.
            pop (str): A string representing the HAPMAP3 population for which the selected genotype corpus was 
                generated.
            model (str): Path to an INI or an XML file containing the epistasis model specification.
            num_snps (int): The number of SNPs in the simulated data.
            num_inds (int): The number of individuals in the simulated data.
            disease_snps (list of int): A list the disease SNPs' position in the selected genotype corpus. If not empty, its size must match the size of the model.
            biased_distr (list of float): Parameters of biased observed phenotype distribution. If empty, no observation bias is applied.
            noise_maf_range (float,float): A tuple of floats between 0 and 1 that specifies the range of acceptable MAFs for the selected noise SNPs.
            disease_maf_range (float,float): A tuple of floats between 0 and 1 that specifies the range of acceptable MAFs for the selected disease SNPs.
            seed (int/None): The seed for numpy.random (possibly None).
            compress (bool): If True, the simulated data is compressed.
        """
        
        # Load genotype corpus.
        print("Loading genotype corpus ...")
        if os.path.exists("corpora/" + str(corpus_id) + "_" + pop + "_genotype.json"):
            with open("corpora/" + str(corpus_id) + "_" + pop + "_genotype.json", "rt") as jsonfile:
                self.genotype = np.asarray(json.load(jsonfile), dtype=np.uint8)
        elif os.path.exists("corpora/" + str(corpus_id) + "_" + pop + "_genotype.json.bz2"):
            with bz2.open("corpora/" + str(corpus_id) + "_" + pop + "_genotype.json.bz2", "rt", encoding="ascii") as zipfile:
                self.genotype = np.asarray(json.load(zipfile), dtype=np.uint8)
        else:
            msg = "Neither the file corpora/" + str(corpus_id) + "_" + pop + "_genotype.json.bz2 "
            msg += "nor the file corpora/" + str(corpus_id) + "_" + pop + "_genotype.json exists. "
            msg += "Change corpus or population ID or re-run generate_genotype_corpus.py." 
            raise OSError(msg)
        
        # Load SNPs.
        print("Loading SNPs ...")
        if os.path.exists("corpora/" + str(corpus_id) + "_" + pop + "_snps.json"):
            with open("corpora/" + str(corpus_id) + "_" + pop + "_snps.json", "rt") as jsonfile:
                self.snps = json.load(jsonfile)
        elif os.path.exists("corpora/" + str(corpus_id) + "_" + pop + "_snps.json.bz2"):
            with bz2.open("corpora/" + str(corpus_id) + "_" + pop + "_snps.json.bz2", "rt", encoding="ascii") as zipfile:
                self.snps = json.load(zipfile)
        else:
            msg = "Neither the file corpora/" + str(corpus_id) + "_" + pop + "_snps.json.bz2 "
            msg += "nor the file corpora/" + str(corpus_id) + "_" + pop + "_snps.json exists. "
            msg += "Change corpus or population ID or re-run generate_genotype_corpus.py." 
            raise OSError(msg)
        
        # Load MAFs.
        print("Loading MAFs ...")
        if os.path.exists("corpora/" + str(corpus_id) + "_" + pop + "_genotype.json"):
            with open("corpora/" + str(corpus_id) + "_" + pop + "_genotype.json", "rt") as jsonfile:
                self.mafs = np.asarray(json.load(jsonfile), dtype=float)
        elif os.path.exists("corpora/" + str(corpus_id) + "_" + pop + "_mafs.json.bz2"):
            with bz2.open("corpora/" + str(corpus_id) + "_" + pop + "_mafs.json.bz2", "rt", encoding="ascii") as zipfile:
                self.mafs = np.asarray(json.load(zipfile), dtype=float)
        else:
            msg = "Neither the file corpora/" + str(corpus_id) + "_" + pop + "_mafs.json.bz2 "
            msg += "nor the file corpora/" + str(corpus_id) + "_" + pop + "_mafs.json exists. "
            msg += "Change corpus or population ID or re-run generate_genotype_corpus.py." 
            raise OSError(msg)
        
        # Load cumulative MAF distribution.
        print("Loading cumulative MAF distribution ...")
        if os.path.exists("corpora/" + str(corpus_id) + "_" + pop + "_cum_mafs.json"):
            with open("corpora/" + str(corpus_id) + "_" + pop + "_cum_mafs.json", "rt") as jsonfile:
                self.cum_mafs = json.load(jsonfile)
        elif os.path.exists("corpora/" + str(corpus_id) + "_" + pop + "_cum_mafs.json.bz2"):
            with bz2.open("corpora/" + str(corpus_id) + "_" + pop + "_cum_mafs.json.bz2", "rt", encoding="ascii") as zipfile:
                self.cum_mafs = json.load(zipfile)
        else:
            msg = "Neither the file corpora/" + str(corpus_id) + "_" + pop + "_cum_mafs.json.bz2 "
            msg += "nor the file corpora/" + str(corpus_id) + "_" + pop + "_cum_mafs.json exists. "
            msg += "Change corpus or population ID or re-run generate_genotype_corpus.py." 
            raise OSError(msg)
        
        # Parse the epistasis model.
        print("Parsing epistasis model ...")
        model_suffix = model.split(".")[-1]
        if model_suffix == "ini":
            self.model = ExtensionalModel(model, seed)
        elif model_suffix == "xml":
            self.model = ParametrizedModel(model, seed)
        else:
            msg = "Unexpected model file suffix " + model_suffix + ". "
            msg += "Valid model file types: ini (for extensional models), xml (for parametrized models)."
            raise ValueError(msg)
        
        # Set remaining attributes.
        self.sim_id = sim_id
        self.num_snps = num_snps
        self.num_inds = num_inds
        self.noise_maf_range = noise_maf_range
        self.disease_maf_range = disease_maf_range
        self.biased_distr = biased_distr
        self.disease_snps = disease_snps
        self.corpus_id = corpus_id
        self.pop = pop
        self.phenotype = None
        self.epsilon = 0.00001
        self.compress = compress
        
        # Set the seed if required.
        if seed != None:
            np.random.seed(seed)
            
        # Ensure that the biased distribution is consistent with the epistasis model.
        print("Checking input consistency ...")
        if len(self.biased_distr) > 0:
            wrong_format = False
            if self.model.phenotype == "quantitative":
                if len(self.biased_distr) != 2:
                    wrong_format = True
                elif self.biased_distr[1] <= 0:
                    wrong_format = True
                if wrong_format:
                    raise ValueError("For quantitative phenotypes, exactly two arguments must be passed to --biased-distr and the second argument must be positive.")
            else:
                if len(self.biased_distr) != self.model.phenotype:
                    wrong_format = True
                else:
                    for p in biased_distr:
                        if p < 0 or p > 1:
                            wrong_format = True
                            break
                    sum_biased = sum(biased_distr)
                    if sum_biased < 1 - self.epsilon or sum_biased > 1 + self.epsilon:
                        wrong_format = True
                if wrong_format:
                    raise ValueError("For categorical phenptypes, the arguments passed to --biased-distr must be non-negative floats that sum up to 1, and their number must match the phenotype dimension.")
                    
        # Ensure that the desired numbers of SNPs and individuals are feasible.
        self.total_num_snps = np.shape(self.genotype)[0]
        self.total_num_inds = np.shape(self.genotype)[1]
        if self.num_snps > self.total_num_snps:
            self.num_snps = self.total_num_snps
            print("WARNING: Desired number of SNPs exceeds SNPs in corpus. Decreased to {}.".format(self.num_snps))
        if self.num_inds > self.total_num_inds:
            self.num_inds = self.total_num_inds
            print("WARNING: Desired number of individuals exceeds individuals in corpus. Decreased to {}.".format(self.num_inds))
            
        # Ensure that the disease SNP set is feasible.
        for snp in self.disease_snps:
            if snp >= self.total_num_snps:
                raise ValueError("Genotype corpus contains no SNP with ID {}.".format(snp))
        if len(self.disease_snps) > 0 and len(self.disease_snps) != self.model.size:
            raise ValueError("The sizes of the disease SNP set and the epistasis model don't match. Disease SNP set size: {}; model size: {}.".format(len(self.disease_snps), self.model.size))
            
        
    def sample_snps(self):
        """Samples the SNPs and the disease SNP set based on the MAFs."""
        
        # Adjust disease MAF range if too few SNPs respect it.
        if len(self.disease_snps) == 0:
            print("Checking disease MAF range (extend if too narrow) ...")
            pos_last_too_small = -1
            pos_last_not_too_large = -1
            for item in self.cum_mafs:
                if float(item[0]) < float(self.disease_maf_range[0]):
                    pos_last_too_small += 1
                if float(item[0]) <= float(self.disease_maf_range[1]):
                    pos_last_not_too_large += 1
            num_cands_too_small = 0
            if pos_last_too_small >= 0:
                num_cands_too_small = self.cum_mafs[pos_last_too_small][1]
            num_cands_not_too_large = 0
            if pos_last_not_too_large >= 0:
                num_cands_not_too_large = self.cum_mafs[pos_last_not_too_large][1]
            adjust_range = False
            while num_cands_not_too_large - num_cands_too_small < self.model.size:
                adjust_range = True
                if pos_last_too_small >= 0:
                    pos_last_too_small -= 1
                    if pos_last_too_small == -1:
                        num_cands_too_small = 0
                    else:
                        num_cands_too_small = self.cum_mafs[pos_last_too_small][1]
                if num_cands_not_too_large - num_cands_too_small < self.model.size:
                    if pos_last_not_too_large < len(self.cum_mafs):
                        pos_last_not_too_large += 1
                        num_cands_not_too_large = self.cum_mafs[pos_last_not_too_large][1]
            if adjust_range:
                self.disease_maf_range[0] = min(self.disease_maf_range[0], self.cum_mafs[pos_last_too_small + 1][0])
                self.disease_maf_range[1] = max(self.disease_maf_range[1], self.cum_mafs[pos_last_not_too_large][0])
                print("WARNING: Specified disease MAF range is too narrow. Extended to [{},{}].".format(self.disease_maf_range[0], self.disease_maf_range[1]))
            
        # Adjust global MAF range if too few SNPs respect it.
        print("Checking global MAF range (extend if too narrow) ...")
        pos_last_too_small = -1
        pos_last_not_too_large = -1
        for item in self.cum_mafs:
            if item[0] < self.noise_maf_range[0]:
                pos_last_too_small += 1
            if item[0] <= self.noise_maf_range[1]:
                pos_last_not_too_large += 1
        num_cands_too_small = 0
        if pos_last_too_small >= 0:
            num_cands_too_small = self.cum_mafs[pos_last_too_small][1]
        num_cands_not_too_large = 0
        if pos_last_not_too_large >= 0:
            num_cands_not_too_large = self.cum_mafs[pos_last_not_too_large][1]
        adjust_range = False
        while num_cands_not_too_large - num_cands_too_small < self.num_snps:
            adjust_range = True
            if pos_last_too_small >= 0:
                pos_last_too_small -= 1
                if pos_last_too_small == -1:
                    num_cands_too_small = 0
                else:
                    num_cands_too_small = self.cum_mafs[pos_last_too_small][1]
            if num_cands_not_too_large - num_cands_too_small < self.num_snps:
                if pos_last_not_too_large < len(self.cum_mafs):
                    pos_last_not_too_large += 1
                    num_cands_not_too_large = self.cum_mafs[pos_last_not_too_large][1]
        if adjust_range:
            self.noise_maf_range[0] = min(self.noise_maf_range[0], self.cum_mafs[pos_last_too_small + 1][0])
            self.noise_maf_range[1] = max(self.noise_maf_range[1], self.cum_mafs[pos_last_not_too_large][0])
            print("WARNING: Specified global MAF range is too narrow. Extended to [{},{}].".format(self.noise_maf_range[0], self.noise_maf_range[1]))
            
        
        # Sample the disease SNPs.
        print("Sampling disease SNPs ...")
        if len(self.disease_snps) == 0:
            candidates = [snp for snp in range(self.total_num_snps) if self.mafs[snp] >= self.disease_maf_range[0] and self.mafs[snp] <= self.disease_maf_range[1]]
            self.disease_snps = np.random.choice(candidates, replace=False, size=self.model.size).tolist()
        is_no_disease_snp = [True] * self.total_num_snps
        for snp in self.disease_snps:
            is_no_disease_snp[snp] = False
            
        # Sample the remaining SNPs.
        print("Sampling remaining SNPs ...")
        candidates = [snp for snp in range(self.total_num_snps) if self.mafs[snp] >= self.noise_maf_range[0] and self.mafs[snp] <= self.noise_maf_range[1] and is_no_disease_snp[snp]]
        selected_snps = sorted(self.disease_snps + np.random.choice(candidates, replace=False, size=(self.num_snps - self.model.size)).tolist())
        
        # Update the genotype and the MAF arrays, as well as the SNP list.
        print("Updating genotype matrix, MAF array, and SNP list ...") 
        self.snps = [self.snps[snp] for snp in selected_snps]
        snp_id_old_to_new = {selected_snps[i] : i for i in range(self.num_snps)}
        self.disease_snps = [snp_id_old_to_new[snp] for snp in self.disease_snps]
        self.genotype = self.genotype[selected_snps,:]
        self.mafs = self.mafs[selected_snps]
        
    def generate_phenotype(self):
        """Generates the phenotype and adjusts the number of individuals."""
        
        # Generate the phenotype for all individuals in the corpus.
        print("Generating the phenotypes ...")
        self.phenotype = np.array([self.model(self.genotype[self.disease_snps,ind]) for ind in range(self.total_num_inds)])
        
        # Subsample the individuals.
        print("Subsampling the individuals ...")
        selected_inds = []
        # No observation bias -> select individuals uniformly.
        if len(self.biased_distr) == 0:
            selected_inds = np.random.choice(range(self.total_num_inds), replace=False, size=self.num_inds).tolist()
        # Model observation bias. Basic idea: Define sampling probabilities for all individuals s.t. randomly drawing them 
        # yields an empirical distribution that is similar to the biased distribution provided by the user.
        else:
            # For quantitative phenotypes, define bins as 1000-quantiles of the biased normal distribution 
            # provided by the user. Then count the number of individuals in each bin, and assign each individual
            # a probability that is negatively proportional to the count in its bin.
            if self.model.phenotype == "quantitative":
                bins = [stats.norm.ppf(q, loc=self.biased_distr[0], scale=self.biased_distr[1]) for q in np.arange(start=0.001,stop=1,step=.001)]
                inds_to_bins = np.digitize(self.phenotype, bins)
                num_inds_in_bins = np.bincount(inds_to_bins)
                probs = 1.0 / np.array([num_inds_in_bins[b] for b in inds_to_bins], dtype=float)
                probs /= np.sum(probs)
            # For categorical phenotypes, the probability of an individual is proportional to the probability of 
            # its phenotype in the biased distribution.
            else:
                pheno_counts = np.bincount(self.phenotype)
                probs = np.array([self.biased_distr[p] / float(pheno_counts[p]) for p in self.phenotype.tolist()], dtype=float)
                probs /= np.sum(probs)
            selected_inds = np.random.choice(range(self.total_num_inds), replace=False, size=self.num_inds, p=probs).tolist()
        
        # Sort the selected individuals and adjust the genotype and phenotype arrays.
        selected_inds = sorted(selected_inds)
        self.genotype = self.genotype[:,selected_inds]
        self.phenotype = self.phenotype[selected_inds]
        
    def dump_simulated_data(self):
        """Dumps the simulated data."""
        
        print("Serializing the simulated data ...")
        # Dump genotype.
        if self.compress:
            with bz2.open("sim/" + str(self.sim_id) + "_" + str(self.corpus_id) + "_" + self.pop + "_genotype.json.bz2", "wt", encoding="ascii") as zipfile:
                json.dump(self.genotype.tolist(), zipfile)
                
            # Dump phenotype.
            with bz2.open("sim/" + str(self.sim_id) + "_" + str(self.corpus_id) + "_" + self.pop + "_phenotype.json.bz2", "wt", encoding="ascii") as zipfile:
                json.dump(self.phenotype.tolist(), zipfile)
                
            # Dump SNPs.
            with bz2.open("sim/" + str(self.sim_id) + "_" + str(self.corpus_id) + "_" + self.pop + "_snps.json.bz2", "wt", encoding="ascii") as zipfile:
                json.dump(self.snps, zipfile)
                
            # Dump disease SNPs.
            with bz2.open("sim/" + str(self.sim_id) + "_" + str(self.corpus_id) + "_" + self.pop + "_disease_snps.json.bz2", "wt", encoding="ascii") as zipfile:
                json.dump(self.disease_snps, zipfile)
                
            # Dump MAFs.
            with bz2.open("sim/" + str(self.sim_id) + "_" + str(self.corpus_id) + "_" + self.pop + "_mafs.json.bz2", "wt", encoding="ascii") as zipfile:
                json.dump(self.mafs.tolist(), zipfile)
        else:
            with open("sim/" + str(self.sim_id) + "_" + str(self.corpus_id) + "_" + self.pop + "_genotype.json", "wt", encoding="ascii") as jsonfile:
                json.dump(self.genotype.tolist(), jsonfile)
                
            # Dump phenotype.
            with open("sim/" + str(self.sim_id) + "_" + str(self.corpus_id) + "_" + self.pop + "_phenotype.json", "wt", encoding="ascii") as jsonfile:
                json.dump(self.phenotype.tolist(), jsonfile)
                
            # Dump SNPs.
            with open("sim/" + str(self.sim_id) + "_" + str(self.corpus_id) + "_" + self.pop + "_snps.json", "wt", encoding="ascii") as jsonfile:
                json.dump(self.snps, jsonfile)
                
            # Dump disease SNPs.
            with open("sim/" + str(self.sim_id) + "_" + str(self.corpus_id) + "_" + self.pop + "_disease_snps.json", "wt", encoding="ascii") as jsonfile:
                json.dump(self.disease_snps, jsonfile)
                
            # Dump MAFs.
            with open("sim/" + str(self.sim_id) + "_" + str(self.corpus_id) + "_" + self.pop + "_mafs.json", "wt", encoding="ascii") as jsonfile:
                json.dump(self.mafs.tolist(), jsonfile)
        