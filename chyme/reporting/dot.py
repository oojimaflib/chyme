"""
 Summary:

    Contains classes for outputting a one-dimensional branched network
    using the DOT graph description language.

 Author:

    Gerald Morgan

 Created:

    20 Jan 2022

"""

class DotOutput:
    """Output class for representing 1d networks as DOT.
    """
    def __init__(self):
        pass

    def to_string(self, net, *args,
                  graphname = "Network Graph", **kwargs):
        dot_str = 'digraph "{}" {{\n'.format(graphname)
        for node in net.nodes:
            dot_str += '"{}" [label="{}"];\n'.format(id(node), node.name)
        for branch in net.branches:
            last_id = '"start_{}"'.format(id(branch))
            dot_str += '"{}" -> {};\n'.format(id(branch.us_node), last_id)
            dot_str += 'subgraph "cluster_{}" {{\n'.format(id(branch))
            dot_str += '{} [label=""];\n'.format(last_id)
            for layer in branch.components:
                next_id = '"layer_{}"'.format(id(layer))
                for component in layer:
                    #dot_str += '"{}" [label="{}"];\n'.format(id(component), component.name)
                    dot_str += '{} -> {} [label="{}"];\n'.format(last_id,
                                                                 next_id,
                                                                 component.name)
                last_id = next_id
                dot_str += '{} [label=""];\n'.format(last_id)
                    
            dot_str += 'label="{}";\n}};\n'.format(branch.name)
            dot_str += '{} -> "{}";\n'.format(last_id, id(branch.ds_node))
            
        dot_str += '}\n'
        return dot_str

    def to_file(self, net, file_like_object, **kwargs):
        file_like_object.write(self.to_string(net, **kwargs))

    def to_filename(self, net, filename, **kwargs):
        with open(filename, 'w') as file_like_object:
            self.to_file(net, file_like_object, **kwargs)
