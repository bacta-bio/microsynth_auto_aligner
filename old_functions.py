
# Pull the containers with the same name as the .gbk files
def get_containers_by_name(benchling, names):
    found_containers = []
    for name in names:
        try:
            # Use server-side name filter to fetch only matching containers
            pages = benchling.containers.list(name=name)
            for page in pages:
                for container in page:
                    if container.name == name:
                        found_containers.append(container)
                        break
                else:
                    continue
                break
        except Exception as e:
            print(f"Error retrieving container {name}: {e}")
    return found_containers

# Find the entities within these containers, and return the sequences
def get_entities_from_containers(benchling, containers):
    entity_dict = {}
    for container in containers:
        try:
            contents = benchling.containers.list_contents(container_id=container.id)
            for item in contents:
                if hasattr(item, 'entity') and item.entity:
                    entity_dict[container.name] = item.entity
                    break  # Only take the first entity
        except Exception as e:
            print(f"Error retrieving sequences from container {container.name}: {e}")
    return entity_dict
