import random
class Fuzzer:
    def __init__(self, grammar):
        self.grammar = grammar

    def fuzz(self, key='<start>', max_num=None, max_depth=None):
        raise NotImplemented()
        
class LimitFuzzer_R(Fuzzer):
    def is_nt(self, name):
        return (name[0], name[-1]) == ('<', '>')
 
    def tree_to_str(self, tree):
        name, children = tree
        if not self.is_nt(name): return name
        return ''.join([self.tree_to_str(c) for c in children])

    def symbol_cost(self, grammar, symbol, seen):
        if symbol in self.key_cost: return self.key_cost[symbol]
        if symbol in seen:
            self.key_cost[symbol] = float('inf')
            return float('inf')
        v = min((self.expansion_cost(grammar, rule, seen | {symbol})
                    for rule in grammar.get(symbol, [])), default=0)
        self.key_cost[symbol] = v
        return v

    def expansion_cost(self, grammar, tokens, seen):
        return max((self.symbol_cost(grammar, token, seen)
                    for token in tokens if token in grammar), default=0) + 1

    def gen_key(self, key, depth, max_depth):
        if key not in self.grammar: return (key, [])
        if depth > max_depth:
            assert key in self.cost
            clst = sorted([(self.cost[key][str(rule)], rule) for rule in self.grammar[key]])
            rules = [r for c,r in clst if c == clst[0][0]]
        else:
            rules = self.grammar[key]
        if not rules:
            raise Exception('Empty key: %s' % key)
        return (key, self.gen_rule(random.choice(rules), depth+1, max_depth))

    def gen_rule(self, rule, depth, max_depth):
        return [self.gen_key(token, depth, max_depth) for token in rule]

    def fuzz(self, key='<start>', max_depth=10):
        return self.tree_to_str(self.gen_key(key=key, depth=0, max_depth=max_depth))

    def __init__(self, grammar):
        super().__init__(grammar)
        self.key_cost = {}
        self.cost = self.compute_cost(grammar)

    def compute_cost(self, grammar):
        cost = {}
        for k in grammar:
            cost[k] = {}
            for rule in grammar[k]:
                cost[k][str(rule)] = self.expansion_cost(grammar, rule, set())
        return cost

class LimitFuzzer(LimitFuzzer_R):
    def nonterminals(self, rule):
        return [t for t in rule if self.is_nt(t)]

    def gen_key(self, key, max_depth):
        def get_def(t):
            if self.is_nt(t):
                return [t, None]
            else:
                return [t, []]

        cheap_grammar = {}
        for k in self.cost:
            # should we minimize it here? We simply avoid infinities
            rules = self.grammar[k]
            min_cost = min([self.cost[k][str(r)] for r in rules])
            #grammar[k] = [r for r in grammar[k] if self.cost[k][str(r)] == float('inf')]
            cheap_grammar[k] = [r for r in self.grammar[k] if self.cost[k][str(r)] == min_cost]

        root = [key, None]
        queue = [(0, root)]
        while queue:
            # get one item to expand from the queue
            (depth, item), *queue = queue
            key = item[0]
            if item[1] is not None: continue
            grammar = self.grammar if depth < max_depth else cheap_grammar
            chosen_rule = random.choice(grammar[key])
            expansion = [get_def(t) for t in chosen_rule]
            item[1] = expansion
            for t in expansion: queue.append((depth+1, t))
            #print("Fuzz: %s" % key, len(queue), file=sys.stderr)
        #print(file=sys.stderr)
        return root

    def fuzz(self, key='<start>', max_depth=10):
        return self.tree_to_str(self.gen_key(key=key, max_depth=max_depth))
if __name__ == '__main__':
    EXPR_GRAMMAR = {'<start>': [['<expr>']],
     '<expr>': [['<term>', ' + ', '<expr>'],
      ['<term>', ' - ', '<expr>'],
      ['<term>']],
     '<term>': [['<factor>', ' * ', '<term>'],
      ['<factor>', ' / ', '<term>'],
      ['<factor>']],
     '<factor>': [['+', '<factor>'],
      ['-', '<factor>'],
      ['(', '<expr>', ')'],
      ['<integer>', '.', '<integer>'],
      ['<integer>']],
     '<integer>': [['<digit>', '<integer>'], ['<digit>']],
     '<digit>': [['0'], ['1'], ['2'], ['3'], ['4'], ['5'], ['6'], ['7'], ['8'], ['9']]}

    f = LimitFuzzer_R(EXPR_GRAMMAR)
    print(f.fuzz('<start>'))

    f = LimitFuzzer(EXPR_GRAMMAR)
    print(f.fuzz('<start>'))
