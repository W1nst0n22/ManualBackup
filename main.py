from datetime import datetime
import getpass
import os
import re
import shutil
import time
import xml.etree.ElementTree as xml
from win11toast import notify, update_progress, toast

# Dates for dated backups
now = time.time()
daily_append = datetime.now().strftime('%Y-%m-%d')
daily_append_regex = re.compile('.*(\.\d{4}-\d{2}\-\d{2})$')  # check this specific format
numbered_append_regex = re.compile('.*(\.\d+)$')

# Current user for share directory
user = getpass.getuser()


def make_toast():
    """
    Create a reusable progress notification
    :return:
    """
    notify(progress={
        'title': '',
        'status': '',
        'value': 'indeterminate',
        'valueStringOverride': ''
    }, duration='long')


def backup_numbered_files(files, directories, backup_location):
    """
    Backup the number-appended files
    :param files: The files to save
    :param directories: The directories to save as zips
    :param backup_location: The location these files & directories exist
    :return: None
    """
    cleanup = []
    for d in directories:
        file = shutil.make_archive(d, 'zip', directories[d])
        files.append(file)
        cleanup.append(file)

    for file in files:
        file_basename = os.path.basename(file)
        copy_to = backup_location + chr(92) + file_basename + '.0'
        try:
            shutil.copy(file, copy_to)
            update_progress({
                'status': 'Backing up files...',
                'valueStringOverride': f'Saving {file_basename}'
            })
            time.sleep(.1)
        except:
            # Failure, new toast
            toast(f'Failed to backup {file}', f'Could not copy  {file} to {copy_to}')

        # Renumber the files in the directory
        numbered_files = {}
        for i in os.listdir(backup_location):
            full_path = backup_location + chr(92) + i
            archive_basename = os.path.basename(full_path)
            # Only remove items that exactly match the backed up file and append pattern
            if archive_basename[0:len(file_basename)] == file_basename and re.match(numbered_append_regex,
                                                                                    archive_basename):
                file_parts = os.path.splitext(archive_basename)
                index = file_parts[1][1:]
                filename = file_parts[0]
                numbered_files[index] = filename

        reversed_files = {}
        for i in sorted(numbered_files.keys(), reverse=True):
            reversed_files[i] = numbered_files[i]

        for i in reversed_files:
            rename_this = backup_location + chr(92) + reversed_files[i] + '.' + str(i)
            to_this = backup_location + chr(92) + reversed_files[i] + '.' + str(int(i) + 1)
            try:
                shutil.copy(rename_this, to_this)
                update_progress({
                    'status': 'Backing up files...',
                    'valueStringOverride': f'Renumbering files'
                })
                time.sleep(.1)
            except:
                # Failure, new toast
                toast(f'Failed to rename {reversed_files[i]}', f'Could not copy  {reversed_files[i]}.{i} to {to_this}')
        os.remove(backup_location + chr(92) + file_basename + '.0')

    # Remove the folder made for the zip
    for cleanup in cleanup:
        os.remove(cleanup)
        update_progress({
            'status': 'Cleaning up...',
            'valueStringOverride': f''
        })
        time.sleep(.1)


def cleanup_numbered_files(files, directories, backup_location, retention):
    """
    Clean up the date-appended files
    :param files: The files previously saved
    :param directories: The directories previously saved as zips
    :param backup_location: The location these files & directories exist
    :param retention: Number of files to keep
    :return:
    """

    update_progress({
        'status': 'Cleaning up old files...',
        'valueStringOverride': f''
    })

    for i in os.listdir(backup_location):
        full_path = backup_location + chr(92) + i
        archive_basename = os.path.basename(full_path)

        for d in directories:
            files.append(directories[d])

        for file in files:
            file_basename = os.path.basename(file)
            # Only remove items that exactly match the backed up file and append pattern
            if archive_basename[0:len(file_basename)] == file_basename and re.match(numbered_append_regex,
                                                                                    archive_basename):
                if int(os.path.splitext(archive_basename)[1][1:]) > int(retention):
                    os.remove(full_path)
    time.sleep(.1)
    update_progress({
        'status': 'Cleaning up old files...',
        'valueStringOverride': f'Done!'
    })


def backup_files():
    """
    Parse the XML to figure out what to backup and how
    :return: None
    """
    config = xml.parse(f'S:{chr(92)}{user}{chr(92)}auto_backups{chr(92)}AutoBackupConfig.xml')
    root = config.getroot()

    backups = root.findall('./')
    total_files = 0

    progress_counter = 0
    for backup in backups:
        retention = backup.attrib['retain']
        backup_location = ''
        files = []
        directories = {}
        for details in backup:
            if details.tag == 'file':
                files.append(details.text)
            if details.tag == 'location':
                backup_location = details.text
            if details.tag == 'directory':
                save_as = os.path.basename(details.text)
                if 'save_as' in details.attrib:
                    save_as = details.attrib['save_as']
                directories[save_as] = details.text

        if not os.path.exists(backup_location):
            os.mkdir(backup_location)
            time.sleep(1)  # Give the OS a chance to make the directory before writing to it.

        if backup.attrib['retain_type'] == 'days':
            backup_daily_files(files, directories, backup_location)
            cleanup_daily_files(files, directories, backup_location, retention)
        if backup.attrib['retain_type'] == 'number':
            backup_numbered_files(files, directories, backup_location)
            cleanup_numbered_files(files, directories, backup_location, retention)

        total_files += len(files) + len(directories)
    return total_files


if __name__ == '__main__':
    make_toast()
    update_progress({'title': 'Running Backup'})
    saved = backup_files()
    time.sleep(.1)
    update_progress({
        'title': 'Backup Complete!',
        'value': 1,
        'status': f'Saved {saved} files'
    })
    time.sleep(.1)
