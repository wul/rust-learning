from collections import namedtuple
import pprint
productions = '''                       
E  -> T E'      
E' -> + T E' | ε
T  -> F T'
T' -> * F T' | ε
F  -> ( E ) | id
'''

CFG = namedtuple('CFG', "NT T P S")
Item = namedtuple('Item', "head body dot lookahead", defaults=('', tuple(), 0, ''))

class Production:
    def __init__(self, str_exp, rank):
        self.rank = rank
        self.head = None
        self.bodies = None
        
        self.production_str = str_exp.strip()
        self.parse_production_str(str_exp)
        
    def deconstruct(self):
        return set([Item(head=self.head, body=tuple(body), dot=0) for body in self.bodies])

        
    def parse_production_str(self, s):
        left, bodies = s.split("->")
        left = left.strip()
        self.head = left

        # Turn bodies from strings to lists
        self.bodies = tuple([body.strip().split() for body in bodies.strip().split("|")])


    def __eq__(self, other):
        return self.rank == other.rank and self.head == other.head

    def __hash__(self):
        return self.production_str.__hash__()

EPSILON = 'ε'
ENDMARKER = '$'

class CFG():

    def __init__(self, productions_str):
        
        # The format of CFG
        # T   : set of terminals
        # NT  : set of non-terminals
        # P   : dict of non-terminals with key as non-terminal
        #     : value is dictionary of production body and derivated terminals pair
        # S   : start symbol
        self.T  = set()
        self.NT = set()
        self.P  = []
        self.S  = None

        # helper varaibles
        # for quick locating production according to production head
        # key:value is NT: index
        self.loc = {}
        self._FIRST = {}
        self._FOLLOW = {}

        self.normalize(productions_str)

        
    def normalize(self, productions):
        idx = 0
        symbol_set = set(productions.replace("->", "").replace("|", " ").split())
    
        for line in productions.splitlines():
            line = line.strip()
            if not line:
                continue

            production = Production(line, idx)
            self.P.append(production)
            
            if self.S is None:
                self.S = production.head
            
            self.NT.add(production.head)
            self.loc[production.head] = idx

            idx += 1

        self.T = symbol_set - self.NT

        # Have to initialize follow/first seperately, because calculation of follow need first set 
        for nt in self.NT:
            self.calculate_first_set(nt)

        for nt in self.NT:
            self.calculate_follow_set(nt)

    def get_production(self, nt):
        try:
            return self.P[self.loc[nt]]
        except KeyError:
            return None

    def __iter__(self):
        return iter(tuple(self.P))

    def is_non_terminal(self, symbol):
        return symbol in self.NT

    def is_terminal(self, symbol):
        return symbol in self.T


    
    def add_to_first_set(self, nt, t, body):
        d = self._FIRST.get(nt, {})
        d[t] = body
        self._FIRST[nt] = d

    def calculate_first_set(self, nt):
        idx = self.loc[nt]
        production = self.P[idx]

        pool = {nt,}
        
        path = []
        def walk(nt, path):
            if nt in path:
                #loop, ignore
                return set()
            
            index = self.loc[nt]
            production = self.P[index]
            chr_set = set()
            for body in production.bodies:
                for symbol in body:
                    if self.is_non_terminal(symbol):
                        new_idx = self.loc[symbol]
                        chrs = walk(symbol, nt)
                        for char in chrs:
                            self.add_to_first_set(nt, char, body)

                            
                        chr_set |= chrs
                        if not EPSILON in chrs:
                            break
                    else:
                        self.add_to_first_set(nt, symbol, body)
                        chr_set.add(symbol)
                        break


            return chr_set
        

        walk(nt, path)


    def calculate_follow_set(self, nt):
        chr_set = {'$'}
        productions = self.P


        rels  = {}
        cache = {}
        
        # Get direct follows for each non-terminals
        # and deduct relations between FOLLOW set of each non-terminals

        for production in self.P:
            left = production.head
            bodies = production.bodies

            for right in bodies:
                check_follow = False
                last_nt      = None
                for symbol in right:
                    if self.is_non_terminal(symbol):

                        if check_follow:
                            symbols = self.FIRST(symbol) - {EPSILON}
                            try:
                                cache[last_nt] |= symbols
                            except KeyError:
                                cache[last_nt] = symbols

                        check_follow = True
                        last_nt = symbol
                    else:
                        # It's terminal
                        if check_follow:
                            symbols = {symbol,}
                            try:
                                cache[last_nt] |= symbols
                            except KeyError:
                                cache[last_nt] = symbols

                        check_follow = False

                # Deduct the relations of FOLLOW sets
                for symbol in reversed(right):
                    if self.is_terminal(symbol):
                        break
                    else:
                        #non-terminal
                        if left != symbol:
                            # ignore self contains
                            try:
                                rels[symbol].add(left)
                            except KeyError:
                                rels[symbol] = {left,}
                    
                        
                        if EPSILON not in self.FIRST(symbol):
                            break

                
        try:
            cache[self.S].add('$')
        except KeyError:
            cache[self.S] = {'$'}
    


        # Calculate all subset of FOLLOW(nt)
        def lookup_relations(nt, rels, st):
            lst = rels.get(nt, set())
            for x in lst:
                if x not in st:
                    st.add(x)
                    lookup_relations(x, rels, st)


    
        chr_set |= cache.get(nt, set())

        subsets = set()
        lookup_relations(nt, rels, subsets)
    
        for symbol in subsets:
            chr_set |= cache.get(symbol, set())
            

        self._FOLLOW[nt] = chr_set
        
    
    def get_first_set_map(self, nt):
        return self._FIRST[nt]

    def get_first_set_of_string(self, s):
        r = set()
        for symbol in s:
            chrs = set()
            if self.is_terminal(symbol):
                chrs.add(symbol)
            else:
                chrs = self.FIRST(symbol)

            r |= chrs
            if not chrs.contains(EPSILON):
                break
        return r

    def FIRST(self, s):
        ret = set()
        for symbol in s.split():
            chrs = set()
            if self.is_terminal(symbol):
                chrs.add(symbol)
            else:
                chrs = set(self._FIRST[symbol].keys())

            ret |= chrs
            if EPSILON not in chrs:
                break
        return ret

    def FOLLOW(self, nt):
        return self._FOLLOW[nt]

                                    

class LL1():
    # FIRST
    def __init__(self, cfg):
        productions = cfg.P
        self.table = {}
        for nt in cfg.NT:
            first_set = cfg.FIRST(nt)
            first_set_map = cfg.FIRST_map(nt)
            for symbol in first_set:
                for body, derivated_terminals in productions[nt].items():
                    if symbol == 'ε':
                        for x in cfg.FOLLOW(nt):
                            table[(nt, x)] = [EPSILON]
                        
                    else:
                        if symbol in derivated_terminals:
                            table[(nt, symbol)] = body


    def print_table(self):
        table = self.table
        pprint.pprint(table)
        rows = set()
        cols = set()
        for row, col in table:
            rows.add(row)
            cols.add(col)
    
        print("Constuction table:")
        print("_____________________________________________________")
        print("{:8s}".format(""), end="")    
        for col in cols:
            print("{:<15s}".format(col), end="")
        print()

        for row in rows:
            print("{:8s}".format(row), end='')
            for col in cols:
                try:
                    body = table[(row,col)]
                    s = row + " -> " + " ".join(body)
                except:
                    s = ""
            
                print("{:<15s}".format(s), end="")
            print("")


class LR0():
    def __init__(self, cfg):
        self._GOTO = {}
        self.cfg = cfg

        # state is set of items
        self._state = {}
        #state = self.CLOSURE(self.cfg.S)

        state = self.CLOSURE2(self.cfg.S)

        state.add(Item(head="S'", body=(cfg.S,), dot=0))
        self._state[0] = state
        self.state_index = 0
        #self.traversal_state()

    def traversal_state(self):
        pool = {self.state_index}
        processed = set()
        
        while True:
            new_states = set()
            for state_idx in pool:
                if state_idx in processed:
                    continue
                
                
                state = self._state[state_idx]
                for X in self.get_next_goto_X(state):
                    new_state = self.GOTO(state, X)
                    new_state_idx = self.get_state_idx(new_state)
                    
                    if new_state_idx is None:
                        self.state_index += 1
                        new_state_idx = self.state_index
                        self._state[new_state_idx] = new_state
                        new_states.add(new_state_idx)
                        
                    self._GOTO[state_idx, X] = new_state_idx
                    
                processed.add(state_idx)

                
            # all states are processed
            if not new_states:
                break
            else:
                pool |= new_states
        
    def get_state_idx(self, state):
        for idx, st in self._state.items():
            if st == state:
                return idx

        return None
        
    def get_next_goto_X(self, state):
        Xs = set()
        for item in state:
            if item.dot < len(item.body) and item.body[item.dot] != EPSILON:
                Xs.add(item.body[item.dot])
        return Xs
    
    def GOTO(self, state, X):
        st = set()
        for item in state:
            if item.dot == len(item.body):
                continue
            if item.body[item.dot] == X:
                item = Item(head=item.head, body=item.body, dot=item.dot+1)
                st.add(item)

        return self.CLOSURE(st)
    
    def __expr__(self):
        return str(self._state) + "\n" + str(self._GOTO)


    def CLOSURE(self, items):
        # Items represents item set
        while True:
            new_items = set()
            for item in items:
                if item.dot >= len(item.body):
                    continue
                
                symbol = item.body[item.dot]
                if self.cfg.is_non_terminal(symbol):
                    production = self.cfg.get_production(symbol)
                    bodies = production.bodies
                    #bodies = self.cfg.P[symbol]
                    for body in bodies:
                        i = Item(head=symbol, body=tuple(body), dot=0)
                        if i not in items:
                            new_items.add(i)
            if not new_items:
                break
            else:
                items |= new_items

        return items
    
    def CLOSURE2(self, nt):
        
        production = self.cfg.get_production(nt)
        items = production.deconstruct()
        return self.CLOSURE(items)

        
    def print(self):
        for idx, state in self._state.items():
            print("{}\t:".format(idx))
            for item in state:
                print("\t{}".format(item))

class LR1():
    pass

if __name__ == '__main__':
    productions = '''
    E -> E + T | T
    T -> T * F | F
    F -> ( E ) | id
    '''
    cfg = CFG(productions)
    ll = LL1(cfg)
    ll.print()
    
    '''
    cfg = CFG(productions)
    print("Calculate FIRSTs")
    for nt in ["E", "T", 'F']:
        print("FIRST({})\t:\t{}".format(nt, cfg.FIRST(nt)))


    print("Print CFG again:")
    pprint.pprint(cfg)

    print("Calculate FOLLOWs")        
    for nt in ['E', "E'", "T", "T'", 'F']:
        print("FOLLOW({})\t:\t{}".format(nt, FOLLOW(nt, cfg)))

    r = LL1(cfg)
    
    print_table(r)
    '''
    parser = LR0(cfg)
    parser.traversal_state()
    parser.print()

