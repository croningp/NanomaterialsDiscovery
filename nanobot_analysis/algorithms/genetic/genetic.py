import random

import numpy

from deap import base
from deap import benchmarks
from deap import creator
from deap import tools


def soft_max(values, temp):
    x = numpy.array(values)
    e = numpy.exp(x / temp)
    soft_max_x = e / numpy.sum(e, axis=0)
    return list(soft_max_x)


def probabilistic_choice(proba_distribution):
    return int(numpy.random.choice(range(len(proba_distribution)), 1, p=proba_distribution))


def proba_normalize(x):
    x = numpy.array(x, dtype=float)
    if numpy.sum(x) == 0:
        x = numpy.ones(x.shape)
    return list(x / numpy.sum(x, dtype=float))


def genome_crossover(genome1, genome2):
    neonate = [None] * len(genome1)

    for i in range(len(neonate)):
        rnd = random.random()
        # 25% of chance to inherit from 1
        if 0 <= rnd < 0.25:
            neonate[i] = genome1[i]
        # 25% of chance to inherit from 2
        elif 0.25 <= rnd < 0.5:
            neonate[i] = genome2[i]
        # 50% of chance to inherit a mix of both
        else:
            # the mix is of random proportion of 1 and 2
            rnd_mix = random.random()
            neonate[i] = rnd_mix * genome1[i] + (1 - rnd_mix) * genome2[i]
    return neonate


def genome_mutation(genome, per_locus_rate, per_locus_SD):
    neonate = list(genome)
    # for each dimension
    for i in range(len(neonate)):
        # with per_locus_rate probability
        if random.random() < per_locus_rate:
            # add a random noise to the gene value following a gaussian distribution
            # of mean 0 and SD of per_locus_SD
            neonate[i] += random.gauss(0, per_locus_SD)
    return neonate


class GA(object):
    """
    A strategy that will keep track of the basic parameters of the GA
    algorithm.
    :param pop_size: Size of the population
    :param part_dim: Number of dimension per genome
    :param pmin: Min value a genome can take for each dimension
    :param pmax: Max value a genome can take for each dimension
    :param n_survivors: Number of survivors to next generation
    :param per_locus_rate: Probability of mutation on each gene (default 0.3)
    :param per_locus_SD: Standard deviation of Gaussian used for the mutation amplitude (default 0.1)
    :param temp: Temperature for the softmax at survival selection step (default 1)
    """

    def __init__(self, pop_size, part_dim, pmin, pmax, n_survivors, *args, **kargs):

        self.pop_size = pop_size
        self.part_dim = part_dim
        self.pmin = pmin
        self.pmax = pmax
        self.n_survivors = n_survivors
        self.per_locus_rate = kargs.get('per_locus_rate', 0.3)
        self.per_locus_SD = kargs.get('per_locus_SD', 0.1)
        self.temp = float(kargs.get('temp', 1))
        self.setup()
        self.generate_init_population()

    def setup(self):
        # We are facing a maximization problem
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)

        self.stats = tools.Statistics(lambda ind: ind.fitness.values)
        self.stats.register("avg", numpy.mean)
        self.stats.register("median", numpy.median)
        self.stats.register("std", numpy.std)
        self.stats.register("min", numpy.min)
        self.stats.register("max", numpy.max)

        self.logbook = tools.Logbook()
        self.logbook.header = ['gen', 'nevals', 'population', 'fitnesses'] + self.stats.fields

        self.gen = 0

    def generate_init_population(self):
        self.population = [self.generate_genome() for _ in range(self.pop_size)]

    def generate_genome(self):
        genome = creator.Individual(random.uniform(self.pmin, self.pmax) for _ in range(self.part_dim))
        return genome

    def generate_empty_genome(self):
        genome = [None for _ in range(self.part_dim)]
        return genome

    def get_next_population(self):
        return self.population

    def set_fitness_value(self, fitnesses):
        for ind, fit in zip(self.population, fitnesses):
            ind.fitness.values = (fit, )

        log_population = [list(x) for x in self.population]
        record = self.stats.compile(self.population)
        self.logbook.record(gen=self.gen, nevals=len(self.population), population=log_population, fitnesses=fitnesses, **record)

        self.update_population()
        self.gen += 1

    def get_fitnesses(self):
        fitnesses = []
        for ind in self.population:
            fitnesses.append(ind.fitness.values[0])
        return fitnesses

    def update_population(self):

        # we make the new population full of None so we are sure it crashes if we do not instanciate them all
        new_population = [self.generate_empty_genome() for _ in range(self.pop_size)]

        survivors_id = self.draw_survivors_id()
        for i in range(len(new_population)):
            # we keep survivors
            if i in survivors_id:
                new_population[i] = self.population[i]
            # and breed new childs
            else:
                new_population[i] = self.breed_one_child()

        self.population = new_population

    def draw_survivors_id(self):
        # survivors are smaple probabilisticaly wrt. their fitness
        fitnesses = self.get_fitnesses()
        # the soft max allow to accentuate more or less the probabily distribution
        # a high temperature make everything more flat, so even looser (less fit) have a chance
        # a low temperatuee make everything sharp, so only the winner (more fit) have a chance
        # temp is a parameter of the algortihm
        x = soft_max(fitnesses, self.temp)

        survivors_id = []
        for _ in range(self.n_survivors):
            x = proba_normalize(x)
            ind = probabilistic_choice(x)

            survivors_id.append(ind)
            # remove the selected one by putting its proba to be selected to 0
            x[ind] = 0

        return survivors_id

    def breed_one_child(self):
        # select 2 parents probabilistically base on their fitness and the softmax
        fitnesses = self.get_fitnesses()
        x = soft_max(fitnesses, self.temp)

        parents = []
        for i in range(2):
            x = proba_normalize(x)
            ind = probabilistic_choice(x)
            parents.append(self.population[ind])
            x[ind] = 0

        # cross the parents
        neonate = genome_crossover(parents[0], parents[1])
        # mutate the child
        neonate = genome_mutation(neonate, self.per_locus_rate, self.per_locus_SD)
        # clip genome within range
        neonate = self.clip_genome(neonate)
        # make the genome a valid individual and return
        return creator.Individual(neonate)

    def clip_genome(self, genome):
        for i in range(len(genome)):
            genome[i] = float(numpy.clip(genome[i], self.pmin, self.pmax))
        return genome

if __name__ == "__main__":

    current_problem = benchmarks.bohachevsky

    def my_evalution_function(my_input):
        minput = [my_input[i] for i in [0, 1]]
        value = current_problem(minput)
        return -value[0]

    params = {'pop_size': 20,
              'part_dim': 3,
              'pmin': -1,
              'pmax': 1,
              'n_survivors': 2,
              'per_locus_rate': 0.3,
              'per_locus_SD': 0.1,
              'temp': 0.1}

    optimizer = GA(**params)

    for _ in range(60):
        pop = optimizer.get_next_population()

        fitnesses = []
        for ind in pop:
            fitnesses.append(my_evalution_function(ind))

        optimizer.set_fitness_value(fitnesses)
