import re
import warnings
from collections import defaultdict
from abc import ABC, abstractclassmethod


## 抽象基类：抽取器
class Extractor(ABC):
    @abstractclassmethod
    def extract(self, text, labels):
        pass


class CombineExtractor(Extractor):
    """组合关系抽取器，把出现的标签直接组合成一组抽取信息"""
    def __init__(self, multival_label=None,sep=","):
        self.sep = sep
        self.multival_label = multival_label

    def extract(self, text, labels):
        item = {item["label_name"]:item["text"] for item in labels}
        if self.multival_label is not None:
            sep = self.sep 
            multival_label = self.multival_label
            item[multival_label] = sep.join([item["text"] for item in labels if item["label_name"]==multival_label])
        return item


class PublisherOrgExtactor(Extractor):
    """ 发布者所属机构抽取器
    """
    def extract(self, text, labels):
        org_labels = filter(lambda x:x["label_name"]=="发布者所属机构",labels)
        orgs = list(map(lambda x:x["text"],org_labels))
        if len(orgs) > 0:
            org = orgs[-1]  # 取最后一个
        else:
            org = None
        item = {"发布者所属机构":org}
        return item


class TradingDirectionExtractor(Extractor):
    """ 交易方向抽取器
    """
    def __init__(self, regexp=None):
        if regexp is None:
            self.p = re.compile('[^：:、\d]{0,2}(?<!卖|买|托)(?P<交易方向>出|收|卖断|买断)\D{0,2}')
        else:
            self._check_regexp(regexp)
            self.p = re.compile(regexp)

    def _check_regexp(self, regexp):
        if "(?P<交易方向>" not in regexp:
            raise ValueError("`regexp` is invalid! must be like `(?P<交易方向>[express])`")

    def extract(self, text, labels):
        m = self.p.search(text)
        return  m.groupdict() if m else dict(交易方向=None)


class MultiSubjectExtractor(Extractor):
    """ 多要素主体抽取器
    用于单条文本中含有多个要素主体的情况，
    如：
       "收12月国贴大商及1.2月国贴城农、财司电商高价票，欢迎清单报价"
       "出少量9月到期双国股，2月到期双国股"
    """
    def __init__(self):
        self.rules = []

    def add_rule(self, rule):
        self.rules.append(rule)

    def add_rules(self, rules):
        self.rules.extend(rules)

    def _join_entity(self, ents):
        join_regexp = "[、,，\s及和/+或者至-]{0,3}"
        _ents = [join_regexp + ent for ent in ents]
        regexp = "|".join(_ents)
        return regexp

    def _build_regexp_patterns(self, tags):
        # 1.准备待填充的要素（正则表达式形式）
        mapping = dict()
        for k, v in tags.items():
            if k in ("承兑人","贴现人","票据期限"):
                val = self._join_entity(v)
                val = "((?:%s)+)"%val
            else:
                val =  "|".join(v)
            mapping[k] = "(?P<{name}>{exp})".format(name=k,exp=val)
        # 2. 填充正则表示式模板
        regexps = []
        for r in self.rules:
            try:
                regexp = r.format_map(mapping)
            except:
                # warnings.warn("rule `%s` fill element %s failed" %(r, mapping))
                continue 
            else:
                regexps.append(regexp)
        # 3. 创建正则表示式对象
        patterns = []
        for regexp in regexps:
            try:
                p = re.compile(regexp)
            except:
                warnings.warn("regexp `%s` compile failed" % regexp)
                continue
            else:
                patterns.append(p)
        return patterns

    def re_extract(self, pattern, text):
        """正则表达式抽取"""
        m = pattern.search(text)
        if m:
            item = m.groupdict()
            item = {k:v for k,v in item.items() if v is not None}        # 过滤None值
            item["matched_info"] = dict(pattern=pattern.pattern, span=m.span())  # 正则表达式匹配信息
            return item
        else:
            return dict()
        
    def _extract(self, text, re_patterns):
        items = [self.re_extract(p, text) for p in re_patterns]
        items = [item for item in items if len(item) > 0]
        if len(items) > 0:
            item = max(items, key=lambda x:len(x))
            # 把已经匹配成功要素在原text中剔除（用`$$$$$$$$`替换），再重新放回进行正则抽取
            start, end = item["matched_info"]["span"]
            new_text = text[:start] + "$$$$$$$$$$$"   + text[end:]
            return [item] + self._extract(new_text, re_patterns)
        else:
            return []
        
    def extract(self, text, labels):
        category = defaultdict(set)
        for info in labels:
            label_type = info["label_name"]
            label_text = info["text"]
            category[label_type].add(label_text)        

        regexps = self._build_regexp_patterns(category)
        rst = self._extract(text, regexps)
        return rst 




class GlobalDiscounterExtractor(Extractor):
    """ 全局贴现人抽取器：贴现人只出现一次，但属于前面出现的所有元素主体
    TODO
    """
    def __init__(self, regexp=None):
        self.p = re.compile("$")  # TODO





class ReExtractor:
    def __init__(self):
        self.rules = list()

    def add_rule(self, rule):
        self.rules.append(rule)

    def _join_entity(self, ents):
        join_regexp = "[、,，\s及和/+或者至-]{0,3}"
        _ents = [join_regexp + ent for ent in ents]
        regexp = "|".join(_ents)
        return regexp

    def _build_regexp(self, tags):
        patterns = []
        mapping = dict()
        for k, v in tags.items():
            if k in ("承兑人","贴现人","票据期限"):
                # v = ["[、,，\s及和/+或者至]{0,3}" + vv for vv in v]
                # val =  "|".join(v)
                val = self._join_entity(v)
                # val = "(%s)+"%val
                val = "((?:%s)+)"%val
            else:
                val =  "|".join(v)
            mapping[k] = "(?P<{name}>{exp})".format(name=k,exp=val)
            
        for r in self.rules:
            try:
                regexp = r.format_map(mapping)
            except:
                warnings.warn("rule `%s` fill element %s failed"%(r, mapping))
                continue 
            else:
                try:
                    p = re.compile(regexp)
                except:
                    warnings.warn("regexp `%s` compile failed"%regexp)
                    continue
                else:
                    patterns.append(p)
        return patterns
    
    def _extract(self, p, text):
        m = p.search(text)
        if m:
            rs = m.groupdict()
            rs = {k:v for k,v in rs.items() if v is not None}
            rs["matched_pattern"] = p.pattern
            return rs
        else:
            return dict()


    def extract(self, text, labels):
        category = defaultdict(set)
        for info in labels:
            label_type = info["label_name"]
            label_text = info["text"]
            category[label_type].add(label_text)        

        regexps = self._build_regexp(category)
        data = [self._extract(r, text) for r in regexps]
        if len(data) > 0:
            rst = max(data, key=lambda x:len(x))
        else:
            rst = dict()
        return rst
    

           