
function saveAction (request)
    --Saves progress for settings, unlocks, alerts and discoveries
    if request.type == 'save_progress' then
        local prefix_profile = (request.save_progress.SETTINGS.profile or 1)..''
        if not love.mod_filesystem.getInfo(prefix_profile) then love.mod_filesystem.createDirectory( prefix_profile ) end
        prefix_profile = prefix_profile..'/'

        if request.save_progress.META then
            compress_and_save(prefix_profile..'meta.jkr', request.save_progress.META)
        end
        compress_and_save('settings.jkr', request.save_progress.SETTINGS)
        if request.save_progress.PROFILE then
            compress_and_save(prefix_profile..'profile.jkr', request.save_progress.PROFILE)
        end
    --Saves the empty profile
    elseif request.type == 'empty_profile' then 
        compress_and_save('settings.jkr', request.save_settings)
        local profile_dir = (request.profile_num or 1)..''
        if not love.mod_filesystem.getInfo(profile_dir) then love.mod_filesystem.createDirectory(profile_dir) end
        if request.save_profile then
            compress_and_save(profile_dir..'/profile.jkr', request.save_profile)
        end
    --Saves the settings file
    elseif request.type == 'save_settings' then 
        compress_and_save('settings.jkr', request.save_settings)
        local profile_dir = (request.profile_num or 1)..''
        if not love.mod_filesystem.getInfo(profile_dir) then love.mod_filesystem.createDirectory(profile_dir) end
        if request.save_profile then
            compress_and_save(profile_dir..'/profile.jkr', request.save_profile)
        end
    --Saves any notifications
    elseif request.type == 'save_notify' then 
        local prefix_profile = (request.profile_num or 1)..''
        if not love.mod_filesystem.getInfo(prefix_profile) then love.mod_filesystem.createDirectory( prefix_profile ) end
        prefix_profile = prefix_profile..'/'

        --if not love.mod_filesystem.getInfo(prefix_profile..'unlock_notify.jkr') then love.mod_filesystem.append( prefix_profile..'unlock_notify.jkr', '') end
        local unlock_notify = get_compressed(prefix_profile..'unlock_notify.jkr') or ''

        if request.save_notify and not string.find(unlock_notify, request.save_notify) then 
            compress_and_save( prefix_profile..'unlock_notify.jkr', unlock_notify..request.save_notify..'\n')
        end

    --Saves the run
    elseif request.type == 'save_run' then 
        local prefix_profile = (request.profile_num or 1)..''
        if not love.mod_filesystem.getInfo(prefix_profile) then love.mod_filesystem.createDirectory( prefix_profile ) end
        prefix_profile = prefix_profile..'/'

        compress_and_save(prefix_profile..'save.jkr', request.save_table)
    end

    if love.filesystem and love.filesystem.sync then
        local ok, err = pcall(love.filesystem.sync)
        if not ok then
            print('[SAVE] filesystem sync failed: '..tostring(err))
        end
    end
end
