def main():
    # set -> no duplicate elements shown (even if present), not ordered
    set1 = {1, 2, 3, 3, 5, 7}
    set2 = {1, 2, 4, 4, 5, 6}
    
    print(set1.difference(set2)) # is inside a but not in b
    print(set1.union(set2), set2.union(set1)) # Show both united
    print(set1.intersection(set2)) # Wat's inside both
    
    # tuple -> orderd, not mutable
    tuple1 = ("one", "two", "three")
    # tuple1.append(4) -> 'tuple' object has no attribute 'append'
    
    # list -> ordered, mutable
    list1 = [1,2,3]
    
    list2 = [1,2,3]
    list3 = [4,5,6]
    list3.append(7)
    
    if list1 is list1:
        print("EXACTLY the same (memory address)")
        
    if list1 is not list2:
        print("NOT EXACTLY the same (memory address)")
    
    if list1 == list2:
        print("Same content")
    
    if list1 != list3:
        print("Not the same content")
        
    # Element in set, list, tuple -> "val" in s_l_t / also for e.g. substring in string
    #val = input("Check if value is in tuple:").lower()
    #print(val in tuple1)
    
    print(range(5), sum(range(5)))
    
    dictTuple = ({'val': 1}, {'val': 1}) # tuple of dictionaries
    
    for obj in dictTuple:
        print(obj.get('val'))
        print(obj['val'])
        
    # Dictionaries
    
    students = {"Bob": 26, "Alice": 23, "Carl": 21}
    
    for key, value in students.items():
        print(f"key: {key} value: {value}")
        
    for key in students.keys():
        print(f"key: {key} value: {students[key]} {students.get(key)}")
        
    for key in students:
        print(f"key: {key} value: {students[key]} {students.get(key)}")
        
    for value in students.values():
        print(f"value: {value}")