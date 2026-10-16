"""Display names and compatibility for frozen historical domain labels."""
LIFESTYLE='生活娱乐'
ALIASES={'生活爱好类':LIFESTYLE,'生活爱好':LIFESTYLE,'生活娱乐类':LIFESTYLE}


def canonical_domain(value):
    return ALIASES.get(value,value)
