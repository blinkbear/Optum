local _M = {}
local function _StrIsEmpty(s)
  return s == nil or s == ''
end
local function _get_namespace()
    local ngx = require "ngx"
    local _namespace = ngx.shared.config:get("namespace")
    if not _namespace then
        ngx.log(ngx.ERR, "Environment variable MY_NAMESPACE not set, using default namespace")
        return "social-network"
    end
    return _namespace 
end


local function _UploadUserId(req_id, post, carrier)
  local GenericObjectPool = require "GenericObjectPool"
  local UserServiceClient = require "social_network_UserService"
  local ngx = ngx
  local namespace = _get_namespace()
  local service_host = "user-service." .. namespace .. ".svc.cluster.local"
  local user_client = GenericObjectPool:connection(
      UserServiceClient, service_host, 9090)
  local status, err = pcall(user_client.UploadCreatorWithUserId, user_client,
      req_id, tonumber(post.user_id), post.username, carrier)
  if not status then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.say("Upload user_id failed: " .. err.message)
    ngx.log(ngx.ERR, "Upload user_id failed: " .. err.message)
    ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
  end
  GenericObjectPool:returnConnection(user_client)
end

local function _UploadText(req_id, post, carrier)
  local GenericObjectPool = require "GenericObjectPool"
  local TextServiceClient = require "social_network_TextService"
  local ngx = ngx

  local namespace = _get_namespace()
  local service_host = "text-service." .. namespace .. ".svc.cluster.local"
  local text_client = GenericObjectPool:connection(
      TextServiceClient, service_host, 9090)
  local status, err = pcall(text_client.UploadText, text_client, req_id,
      post.text, carrier)
  if not status then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.say("Upload text failed: " .. err.message)
    ngx.log(ngx.ERR, "Upload text failed: " .. err.message)
    ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
  end
  GenericObjectPool:returnConnection(text_client)
end

local function _UploadUniqueId(req_id, post, carrier)
  local GenericObjectPool = require "GenericObjectPool"
  local UniqueIdServiceClient = require "social_network_UniqueIdService"
  local ngx = ngx
  
  local namespace = _get_namespace()
  local service_host = "unique-id-service." .. namespace .. ".svc.cluster.local"
  local unique_id_client = GenericObjectPool:connection(
      UniqueIdServiceClient,service_host , 9090)
  local status, err = pcall(unique_id_client.UploadUniqueId, unique_id_client,
      req_id, tonumber(post.post_type), carrier)
  if not status then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.say("Upload unique_id failed: " .. err.message)
    ngx.log(ngx.ERR, "Upload unique_id failed: " .. err.message)
    ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
  end
  GenericObjectPool:returnConnection(unique_id_client)
end

local function _UploadMedia(req_id, post, carrier)
  local GenericObjectPool = require "GenericObjectPool"
  local MediaServiceClient = require "social_network_MediaService"
  local cjson = require "cjson"
  local ngx = ngx

  local namespace = _get_namespace()
  local service_host = "media-service." .. namespace .. ".svc.cluster.local"
  local media_client = GenericObjectPool:connection(
      MediaServiceClient, service_host, 9090)
  local status, err
  if (not _StrIsEmpty(post.media_ids) and not _StrIsEmpty(post.media_types)) then
    status, err = pcall(media_client.UploadMedia, media_client,
        req_id, cjson.decode(post.media_types), cjson.decode(post.media_ids), carrier)
  else
    status, err = pcall(media_client.UploadMedia, media_client,
        req_id, {}, {}, carrier)
  end
  if not status then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.say("Upload media failed: " .. err.message)
    ngx.log(ngx.ERR, "Upload media failed: " .. err.message)
    ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
  end
  GenericObjectPool:returnConnection(media_client)
end

function _M.ComposePost()
  local bridge_tracer = require "opentracing_bridge_tracer"
  local ngx = ngx
  local cjson = require "cjson"
  local jwt = require "resty.jwt"

  local req_id = tonumber(string.sub(ngx.var.request_id, 0, 15), 16)
  local tracer = bridge_tracer.new_from_global()
  local parent_span_context = tracer:binary_extract(ngx.var.opentracing_binary_context)
  local span = tracer:start_span("ComposePost",
      { ["references"] = { { "child_of", parent_span_context } } })
  local carrier = {}
  tracer:text_map_inject(span:context(), carrier)

  ngx.req.read_body()
  local post = ngx.req.get_post_args()

  if (_StrIsEmpty(post.user_id) or _StrIsEmpty(post.username) or
      _StrIsEmpty(post.post_type) or _StrIsEmpty(post.text)) then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("Incomplete arguments")
    ngx.log(ngx.ERR, "Incomplete arguments")
    ngx.exit(ngx.HTTP_BAD_REQUEST)
  end

  local threads = {
    ngx.thread.spawn(_UploadMedia, req_id, post, carrier),
    ngx.thread.spawn(_UploadUserId, req_id, post, carrier),
    ngx.thread.spawn(_UploadText, req_id, post, carrier),
    ngx.thread.spawn(_UploadUniqueId, req_id, post, carrier)
  }

  local status = ngx.HTTP_OK
  for i = 1, #threads do
    local ok, res = ngx.thread.wait(threads[i])
    if not ok then
      status = ngx.HTTP_INTERNAL_SERVER_ERROR
      ngx.exit(status)
    end
  end
  ngx.say("Successfully upload post")
  span:finish()
  ngx.exit(status)
end




return _M
