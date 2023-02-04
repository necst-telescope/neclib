class Ordinal(int):
    """Integer, with corresponding suffix as ordinal number in string representation.

    Examples
    --------
    >>> Ordinal(1)
    1
    >>> f"{Ordinal(1)}"
    '1st'
    >>> f"{Ordinal(2)} parameter"
    '2nd parameter'

    """

    def __format__(self, format_spec: str) -> str:
        number = str(self)
        if self < 0:
            return number
        elif (self % 10 == 1) and (self % 100 != 11):
            return number + "st"
        elif (self % 10 == 2) and (self % 100 != 12):
            return number + "nd"
        elif (self % 10 == 3) and (self % 100 != 13):
            return number + "rd"
        else:
            return number + "th"
