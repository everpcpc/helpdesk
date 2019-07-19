# coding: utf-8

import logging

from app.libs.decorators import cached_property_with_ttl
from app.models.action import Action
from app.models.provider import get_provider
from app.config import ACTION_TREE_CONFIG, PROVIDER

logger = logging.getLogger(__name__)

# objs = {}


class ActionTree:
    def __init__(self, tree_config, level=0):
        self.name = None
        self._nexts = []
        self.parent = None
        self.action = None
        self.is_leaf = False
        self.level = level
        self.config = tree_config

        self.build_from_config(tree_config)

    def __str__(self):
        return 'ActionTree(%s, level=%s)' % (self.config, self.level)

    __repr__ = __str__

    def build_from_config(self, config):
        assert type(config) is list, 'expect %s, got %s: %s' % ('list', type(config), config)
        if not config:
            return
        self.name = config[0]
        if any(not isinstance(c, str) for c in config):
            for subconfig in config[1]:
                subtree = ActionTree(subconfig, level=self.level + 1)
                subtree.parent = self
                self._nexts.append(subtree)
        else:
            # leaf
            provider_object = config[-1]

            # # dedup
            # system_provider = get_provider(PROVIDER)
            # default_pack = system_provider.get_default_pack() + '.'
            # if not provider_object.endswith('.'):
            #     if provider_object.startswith(default_pack):
            #         provider_object = provider_object[len(default_pack):]
            # if provider_object in objs:
            #     return
            # objs[provider_object] = True

            if provider_object.endswith('.'):
                # pack
                pack_sub_tree_config = self.resolve_pack(*config)
                self.build_from_config(pack_sub_tree_config)
            else:
                # leaf action
                self.action = Action(*config)
                self.is_leaf = True

    def resolve_pack(self, *config):
        name = config[0]
        provider_object = config[-1]
        pack = provider_object[:-1]

        sub_actions = []
        system_provider = get_provider(PROVIDER)
        actions = system_provider.get_actions(pack=pack)
        for a in actions:
            obj = '.'.join([a.get('pack'), a.get('name')])
            desc = a.get('description')
            sub_actions.append([obj, desc, obj])
        return [name, sub_actions]

    @cached_property_with_ttl(300)
    def nexts(self):
        # if is pack, re-calc it
        if all(isinstance(c, str) for c in self.config):
            if self.config[-1].endswith('.'):
                logger.warn('recalc %s', self)
                self._nexts = []
                pack_sub_tree_config = self.resolve_pack(*self.config)
                self.build_from_config(pack_sub_tree_config)

        return self._nexts

    @property
    def key(self):
        return '{level}-{name}'.format(level=self.level, name=self.name)

    def first(self):
        if self.action:
            return self
        if not self._nexts:
            return self
        return self._nexts[0].first()

    def find(self, obj):
        if not obj:
            return None
        if self.action:
            return self if self.action.target_object == obj else None
        for sub in self._nexts:
            ret = sub.find(obj)
            if ret is not None:
                return ret

    def path_to(self, tree_node, pattern='{level}-{name}'):
        if not tree_node:
            return []
        return self.path_to(tree_node.parent, pattern) + [pattern.format(**tree_node.__dict__) if pattern else tree_node]

    def get_tree_list(self, node_formatter):
        """
        以嵌套列表的方式返回action_tree
        :param: node_formatter: 节点处理函数
        :return: 嵌套的列表
        """
        local_list = []

        for node in self.nexts:
            if node.is_leaf:
                local_list.append(node_formatter(node, local_list))
                continue
            children_list = node.get_tree_list(node_formatter)
            local_list.append(node_formatter(node, children_list))

        if self.parent is None:
            local_list = node_formatter(self, local_list)
        return local_list


action_tree = ActionTree(ACTION_TREE_CONFIG)
